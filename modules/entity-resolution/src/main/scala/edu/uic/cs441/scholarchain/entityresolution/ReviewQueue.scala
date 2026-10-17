package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path, StandardOpenOption}
import scala.collection.mutable
import scala.util.Try
import upickle.default.{ReadWriter, write, writeJs}

final case class ReviewSampling(
    schemaVersion: String,
    seed: String,
    development: Int,
    heldOut: Int,
    developmentReserve: Int,
    heldOutReserve: Int,
    maxPopulationPairs: Int
) derives ReadWriter
object ReviewSampling {
  val standard = ReviewSampling(
    "scholarchain.review-sampling.v1",
    "scholarchain-5c-2026",
    40,
    200,
    10,
    50,
    100000
  )
  def validate(s: ReviewSampling): Unit = {
    require(
      s.schemaVersion == standard.schemaVersion && s.seed.nonEmpty && s.seed.length <= 256,
      "invalid sampling version/seed"
    )
    require(
      Vector(s.development, s.heldOut)
        .forall(_ > 0) && Vector(s.developmentReserve, s.heldOutReserve).forall(_ >= 0),
      "invalid review allocation"
    )
    require(
      s.maxPopulationPairs > 0 && s.development.toLong + s.heldOut + s.developmentReserve + s.heldOutReserve <= s.maxPopulationPairs,
      "invalid population bound"
    )
  }
}
final case class ReviewPopulationBinding(
    inputEvidenceHash: String,
    candidatePopulationHash: String
) derives ReadWriter

/** Prediction-run metadata; this is deliberately absent from human label identity. */
final case class ReviewBinding(
    inputEvidenceHash: String,
    candidatePopulationHash: String,
    policyHash: String,
    configHash: String,
    promptHash: String,
    responseSchemaHash: String,
    modelIdentity: String,
    codeRevision: String,
    sourceTreeHash: String
) derives ReadWriter
final case class ReviewTask(
    pair: ResolutionPair,
    groupIds: Vector[String],
    partition: String,
    role: String,
    stratum: String,
    evidenceHash: String,
    leftEvidence: Vector[EvidenceRecord],
    rightEvidence: Vector[EvidenceRecord],
    candidateRefs: Vector[CandidateBlockRef]
) derives ReadWriter
final case class LeakageGroup(
    groupId: String,
    endpointIds: Vector[String],
    anchorHashes: Vector[String]
) derives ReadWriter
final case class ReviewSplit(
    schemaVersion: String,
    sourcePopulationHash: String,
    candidatePopulationHash: String,
    sampling: ReviewSampling,
    groups: Vector[LeakageGroup],
    partitions: Map[String, String],
    pairGroups: Map[String, Vector[String]],
    excludedCrossPartition: Int,
    selected: Map[String, String],
    residualRisks: Vector[String]
) derives ReadWriter {
  def hash: String = StrictJson.hash(this)
}
final case class ReviewQueueDocument(
    schemaVersion: String,
    queueId: String,
    queueHash: String,
    sourcePopulationHash: String,
    splitHash: String,
    binding: ReviewPopulationBinding,
    tasks: Vector[ReviewTask]
) derives ReadWriter
final case class ReviewArtifacts(
    queue: ReviewQueueDocument,
    split: ReviewSplit,
    generationBinding: Option[ReviewBinding] = None
) derives ReadWriter

/** Sampling consumes observations and candidate evidence only, never matcher outcomes or labels. */
object ReviewQueue {
  val queueVersion = "scholarchain.review-queue.v1"
  val splitVersion = "scholarchain.review-split.v1"
  def populationHash(population: CandidatePopulation): String = StrictJson.hash(population)
  def populationBinding(b: ReviewBinding): ReviewPopulationBinding =
    ReviewPopulationBinding(b.inputEvidenceHash, b.candidatePopulationHash)
  def checkPopulationBinding(b: ReviewPopulationBinding): Unit =
    require(
      Vector(b.inputEvidenceHash, b.candidatePopulationHash).forall(_.matches("[0-9a-f]{64}")),
      "invalid population binding hash"
    )
  def checkBinding(b: ReviewBinding): Unit = {
    require(
      Vector(
        b.inputEvidenceHash,
        b.candidatePopulationHash,
        b.policyHash,
        b.configHash,
        b.promptHash,
        b.responseSchemaHash,
        b.sourceTreeHash
      ).forall(_.matches("[0-9a-f]{64}")),
      "invalid binding hash"
    )
    require(
      b.codeRevision.matches(
        "[0-9a-f]{40}"
      ) && b.modelIdentity.nonEmpty && b.modelIdentity.length <= 256,
      "invalid code/model identity"
    )
  }
  private def taskEvidenceHash(t: ReviewTask): String = StrictJson.hash(t.copy(evidenceHash = ""))
  private def hashQueue(q: ReviewQueueDocument): String =
    StrictJson.hash(q.copy(queueId = "", queueHash = ""))
  private def observationKey(e: ResolutionEndpoint): String = {
    val r = ResolutionIds.observation(e)
    // Deliberately omit snapshot: copies at different retrievals are not independent evidence.
    s"observation:${r.source.wire}:${r.sourceRecordId}"
  }
  private def tokens(e: ResolutionEndpoint, input: ResolutionInput): Set[String] = {
    val w = input.parentWork(e)
    val base = Set(observationKey(e)) ++ input
      .authority(e)
      .map((ns, v) =>
        (if (ns == ResolutionAuthorityNamespace.Orcid) "identity:"
         else "authority:") + ns.wire + ":" + v
      )
    val work = w.toSet.flatMap { record =>
      val title = Normalization.nameTokens(record.title).distinct.sorted.mkString(" ")
      val words = title.split(" ").filter(_.nonEmpty).toVector.take(256)
      val nearTitles =
        if (words.size >= 6)
          words.indices.map(i => "near-title:" + words.patch(i, Nil, 1).mkString(" ")).toSet
        else Set.empty[String]
      val workAuthority = input.authority
        .getOrElse(
          ResolutionEndpoint.Work(ResolutionInput.ref(record.provenance), record.workId),
          Set.empty
        )
        .map((ns, v) => "authority:" + ns.wire + ":" + v)
      Set("work:" + record.workId) ++ workAuthority ++ nearTitles ++ Option
        .when(title.nonEmpty)("title:" + title)
        .toSet ++ record.authors.flatMap { m =>
        m.observedOrcid.map("identity:orcid:" + _).toVector ++ m.observedOpenAlexAuthorId.map(
          "identity:openalex:" + _
        )
      }
    }
    val mention = input
      .mention(e)
      .toSet
      .flatMap(m =>
        m.observedOrcid.map("identity:orcid:" + _).toSet ++ m.observedOpenAlexAuthorId
          .map("identity:openalex:" + _)
      )
    base ++ work ++ mention
  }
  def build(
      input: ResolutionInput,
      population: CandidatePopulation,
      sampling: ReviewSampling,
      binding: ReviewBinding
  ): Either[String, ReviewArtifacts] = Try {
    ReviewSampling.validate(sampling); checkBinding(binding)
    require(
      binding.inputEvidenceHash == input.inputEvidenceHash && binding.candidatePopulationHash == populationHash(
        population
      ),
      "binding differs from source/candidate population"
    )
    require(
      population.pairs.nonEmpty && population.pairs.size <= sampling.maxPopulationPairs && population.pairs
        .map(_.pair.pairId)
        .distinct
        .size == population.pairs.size,
      "empty, duplicate or oversized candidate population"
    )
    val allEvidence = input.evidence ++ population.derivedEvidence.map(e => e.ref -> e)
    val pairs = population.pairs.sortBy(_.pair.pairId)
    pairs.foreach { d =>
      require(ResolutionValidation.check(d.pair, input.context).isRight, "invalid candidate pair")
      require(d.evidenceRefs.forall(allEvidence.contains), "candidate references missing evidence")
    }
    val endpoints = input.endpoints.distinct.sortBy(ResolutionIds.endpointKey)
    val endpointIndex = endpoints.zipWithIndex.toMap
    val parent = Array.tabulate(endpoints.size)(identity)
    def root(n: Int): Int = {
      var r = n; while (parent(r) != r) r = parent(r); var x = n;
      while (parent(x) != x) { val next = parent(x); parent(x) = r; x = next }; r
    }
    val seen = mutable.Map.empty[String, Int]
    val anchors = endpoints.map(e => tokens(e, input).toVector.sorted)
    anchors.zipWithIndex.foreach { (as, i) =>
      as.foreach { a => seen.get(a).fold { seen(a) = i } { j => parent(root(i)) = root(j) } }
    }
    val groups = endpoints.indices
      .groupBy(root)
      .values
      .toVector
      .map { indexes =>
        val ids = indexes.map(i => ResolutionIds.endpointId(endpoints(i))).sorted.toVector
        val ah = indexes.flatMap(i => anchors(i)).distinct.sorted.map(StableIds.sha256Hex).toVector
        LeakageGroup("review-group:" + StableIds.sha256Hex(ids.mkString("\n")), ids, ah)
      }
      .sortBy(_.groupId)
    val groupOfEndpoint = groups.flatMap(g => g.endpointIds.map(_ -> g.groupId)).toMap
    val pairGroups = pairs
      .map(d =>
        d.pair.pairId -> Vector(d.pair.left, d.pair.right)
          .map(e => groupOfEndpoint(ResolutionIds.endpointId(e)))
          .distinct
          .sorted
      )
      .toMap
    val devNeed = sampling.development + sampling.developmentReserve
    val heldNeed = sampling.heldOut + sampling.heldOutReserve
    require(
      pairs.size >= devNeed + heldNeed,
      s"INFEASIBLE_POPULATION: ${pairs.size} unique pairs; need ${devNeed + heldNeed}"
    )
    // Candidate edges do not create identity groups. Assign whole evidence groups; discard
    // cross-partition candidate edges. Greedy bounded search never falls back to pair splitting.
    val degrees = pairGroups.values.flatten.toVector.groupMapReduce(identity)(_ => 1)(_ + _)
    val devGroups = mutable.Set.empty[String]
    val allGroups = groups.map(_.groupId).toSet
    val incidence = pairGroups.toVector.flatMap((id, gs) => gs.map(_ -> id)).groupMap(_._1)(_._2)
    val devInside = mutable.Set.empty[String]
    val heldInside = mutable.Set.from(pairGroups.keys)
    val byId = pairs.map(d => d.pair.pairId -> d).toMap
    val entities = pairs.map(_.pair.entityType).distinct.sortBy(_.toString)
    val totals = pairs.groupMapReduce(_.pair.entityType)(_ => 1)(_ + _)
    // Balance observable entity coverage before choosing whole development components.
    // These are sampling targets, not claims about unknown same/different gold classes.
    val entityTargets = entities
      .map(e => e -> math.min(totals(e), (devNeed + entities.size - 1) / entities.size))
      .toMap
    val devCounts = mutable.Map.from(entities.map(_ -> 0))
    val heldCounts = mutable.Map.from(totals)
    def rank(d: DerivedPair): (Int, String) =
      (
        pairGroups(d.pair.pairId).map(degrees).sum,
        StableIds.sha256Hex(sampling.seed + d.pair.pairId)
      )
    val searches = entities.map { e =>
      val strata = pairs
        .filter(_.pair.entityType == e)
        .groupBy(d => stratum(d.pair, input))
        .toVector
        .sortBy(_._1)
        .map((_, ds) => ds.sortBy(rank))
      e -> (0 until strata.map(_.size).max).iterator.flatMap(n => strata.flatMap(_.lift(n)))
    }.toMap
    var work = 0L
    def needsCoverage: Boolean = entities.exists(e => devCounts(e) < entityTargets(e))
    while (searches.values.exists(_.hasNext) && (devInside.size < devNeed || needsCoverage)) {
      val available = entities.filter(e => searches(e).hasNext)
      val entity =
        available.minBy(e => (devCounts(e).toDouble / math.max(1, entityTargets(e)), e.toString))
      val d = searches(entity).next()
      val newGroups = pairGroups(d.pair.pairId).filterNot(devGroups)
      val affected = newGroups.flatMap(g => incidence(g)).distinct
      work += affected.size
      require(
        work <= 5000000L,
        "INFEASIBLE_SELECTION_SEARCH_BOUND: conservative grouped search exceeded five million incident edges; expand population or revise sampling with a recorded decision"
      )
      val lostHeld = affected.filter(heldInside)
      val lostByEntity = lostHeld.groupMapReduce(id => byId(id).pair.entityType)(_ => 1)(_ + _)
      // Preserve at least one held-out comparison for an entity when population permits.
      val preservesEntity =
        entities.forall(e => totals(e) < 2 || heldCounts(e) - lostByEntity.getOrElse(e, 0) >= 1)
      if (heldInside.size - lostHeld.size >= heldNeed && preservesEntity) {
        devGroups ++= newGroups
        heldInside --= lostHeld
        lostByEntity.foreach((e, n) => heldCounts(e) -= n)
        val gained = affected.filter(id => !devInside(id) && pairGroups(id).forall(devGroups))
        devInside ++= gained
        gained.foreach(id => devCounts(byId(id).pair.entityType) += 1)
      }
    }
    require(
      devInside.size >= devNeed && heldInside.size >= heldNeed,
      s"INFEASIBLE_GROUPED_SELECTION: ${groups.size} leakage groups; retained development=${devInside.size}, held-out=${heldInside.size}; need $devNeed/$heldNeed. Deterministic conservative selection found no allocation; expand population; no pair-split fallback."
    )
    val partitions =
      groups.map(g => g.groupId -> (if (devGroups(g.groupId)) "development" else "held-out")).toMap
    val retained = pairs.filter(d => pairGroups(d.pair.pairId).map(partitions).distinct.size == 1)
    def ranked(partition: String): Vector[String] = {
      val candidates = retained
        .filter(d => pairGroups(d.pair.pairId).forall(g => partitions(g) == partition))
        .map(_.pair.pairId)
      // First round-robin evidence strata within each entity, then round-robin entities.
      // A richer stratum catalog must not multiply one entity's sampling weight.
      val perEntity =
        candidates.groupBy(id => byId(id).pair.entityType).toVector.sortBy(_._1.toString).map {
          (_, ids) =>
            val buckets = ids
              .groupBy(id => stratum(byId(id).pair, input))
              .toVector
              .sortBy(_._1)
              .map((_, vs) => vs.sortBy(id => StableIds.sha256Hex(sampling.seed + id)))
            (0 until buckets.map(_.size).max).toVector.flatMap(n => buckets.flatMap(_.lift(n)))
        }
      (0 until perEntity.map(_.size).max).toVector.flatMap(n => perEntity.flatMap(_.lift(n)))
    }

    val selected = Vector(
      ("development", sampling.development, sampling.developmentReserve),
      ("held-out", sampling.heldOut, sampling.heldOutReserve)
    ).flatMap { (partition, initial, reserve) =>
      ranked(partition).take(initial + reserve).zipWithIndex.map { case (id, n) =>
        id -> (if (n < initial) "initial" else "reserve")
      }
    }.toMap
    val sourceHash =
      StrictJson.hash(input.evidence.toVector.sortBy(_._1).map((ref, e) => ref -> e.sha256))
    val split = ReviewSplit(
      splitVersion,
      sourceHash,
      populationHash(population),
      sampling,
      groups.sortBy(_.groupId),
      partitions,
      pairGroups,
      pairs.size - retained.size,
      selected,
      Vector(
        "Unobserved identities and title paraphrases may leak across partitions; known source/identifier/title anchors are grouped.",
        "Metrics describe sampled candidate pairs; blocking recall and global identity recall are unmeasured.",
        "Evidence strata are oversampled without population weights; no population accuracy claim is justified.",
        "Development entity coverage targets=" + entities
          .map(e => e.toString + ":" + entityTargets(e) + "/available:" + devCounts(e))
          .mkString(",") + "; component connectivity may prevent balance; actual selected counts must be reported."
      )
    )
    val tasks = selected.toVector.sortBy((id, _) => StableIds.sha256Hex(sampling.seed + id)).map {
      (id, role) =>
        val d = byId(id); val gs = pairGroups(id)
        def evidence(e: ResolutionEndpoint) = input.refs(e).map(allEvidence)
        val t = ReviewTask(
          d.pair,
          gs,
          partitions(gs.head),
          role,
          stratum(d.pair, input),
          "",
          evidence(d.pair.left),
          evidence(d.pair.right),
          d.contributingCandidates
        )
        t.copy(evidenceHash = taskEvidenceHash(t))
    }
    val unsigned = ReviewQueueDocument(
      queueVersion,
      "",
      "",
      sourceHash,
      split.hash,
      populationBinding(binding),
      tasks
    )
    val hash = hashQueue(unsigned)
    val result =
      ReviewArtifacts(
        unsigned.copy(queueId = "review-queue:" + hash, queueHash = hash),
        split,
        Some(binding)
      )
    validate(result.queue, result.split).fold(e => throw new IllegalArgumentException(e), identity)
    result
  }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getSimpleName))
  private def stratum(p: ResolutionPair, input: ResolutionInput): String = {
    val left = input.authority(p.left); val right = input.authority(p.right)
    if (left.exists((ns, v) => right.exists((rn, rv) => ns == rn && v != rv)))
      "observed-id-disagreement"
    else if (left.intersect(right).nonEmpty) "shared-observed-id"
    else if (left.isEmpty || right.isEmpty) "missing-authoritative-id"
    else "other-observed-evidence"
  }
  def validateQueue(q: ReviewQueueDocument): Either[String, ReviewQueueDocument] = Try {
    checkPopulationBinding(q.binding)
    require(
      q.schemaVersion == queueVersion && q.queueHash == hashQueue(
        q
      ) && q.queueId == "review-queue:" + q.queueHash,
      "queue identity/hash mismatch"
    )
    require(
      q.sourcePopulationHash.matches("[0-9a-f]{64}") && q.splitHash.matches("[0-9a-f]{64}"),
      "invalid queue population/split hash"
    )
    require(
      q.tasks.nonEmpty && q.tasks.map(_.pair.pairId).distinct.size == q.tasks.size,
      "empty/duplicate queue pairs"
    )
    q.tasks.foreach { t =>
      require(
        Set("development", "held-out")(t.partition) && Set("initial", "reserve")(
          t.role
        ) && t.groupIds.nonEmpty && t.groupIds.forall(_.startsWith("review-group:")),
        "invalid task assignment"
      )
      require(
        ResolutionIds.pair(t.pair.entityType, t.pair.left, t.pair.right).contains(t.pair),
        "noncanonical queue pair"
      )
      require(
        t.evidenceHash == taskEvidenceHash(
          t
        ) && t.leftEvidence.nonEmpty && t.rightEvidence.nonEmpty,
        "task evidence mismatch"
      )
      (t.leftEvidence ++ t.rightEvidence).foreach(e =>
        require(
          e.sha256 == StableIds.sha256Hex(
            StrictJson.canonical(e.payload)
          ) && e.ref == ResolutionInput.evidenceFor(e.kind, e.payload),
          "corrupt queue evidence"
        )
      )
    }
    q
  }.toEither.left.map(_.getMessage)
  def validate(q: ReviewQueueDocument, s: ReviewSplit): Either[String, ReviewArtifacts] = Try {
    validateQueue(q).fold(e => throw new IllegalArgumentException(e), identity);
    ReviewSampling.validate(s.sampling)
    require(
      s.schemaVersion == splitVersion && q.splitHash == s.hash && q.sourcePopulationHash == s.sourcePopulationHash && q.binding.candidatePopulationHash == s.candidatePopulationHash,
      "split identity/hash mismatch"
    )
    require(
      s.groups.map(_.groupId).distinct.size == s.groups.size && s.partitions.keySet == s.groups
        .map(_.groupId)
        .toSet,
      "invalid group partition inventory"
    )
    require(
      s.groups.flatMap(_.endpointIds).distinct.size == s.groups.map(_.endpointIds.size).sum,
      "endpoint crosses leakage groups"
    )
    val byEndpoint = s.groups.flatMap(g => g.endpointIds.map(_ -> g.groupId)).toMap
    require(
      s.selected.keySet == q.tasks.map(_.pair.pairId).toSet,
      "split/queue selected inventory mismatch"
    )
    q.tasks.foreach { t =>
      val gs = Vector(t.pair.left, t.pair.right)
        .map(e => byEndpoint.getOrElse(ResolutionIds.endpointId(e), ""))
        .distinct
        .sorted
      require(
        gs == t.groupIds && s.pairGroups.get(t.pair.pairId).contains(gs) && gs.forall(g =>
          s.partitions.get(g).contains(t.partition)
        ) && s.selected(t.pair.pairId) == t.role,
        "task/group partition mismatch"
      )
    }
    val anchors = s.groups.flatMap(g => g.anchorHashes.map(_ -> s.partitions(g.groupId)))
    require(
      anchors.groupMap(_._1)(_._2).values.forall(_.distinct.size == 1),
      "anchor leaks across partitions"
    )
    Vector(
      ("development", "initial", s.sampling.development),
      ("held-out", "initial", s.sampling.heldOut),
      ("development", "reserve", s.sampling.developmentReserve),
      ("held-out", "reserve", s.sampling.heldOutReserve)
    ).foreach { (p, r, n) =>
      require(
        q.tasks.count(t => t.partition == p && t.role == r) == n,
        "incorrect review allocation"
      )
    }
    ReviewArtifacts(q, s)
  }.toEither.left.map(_.getMessage)
  def parseQueue(text: String): Either[String, ReviewQueueDocument] =
    StrictJson.parse[ReviewQueueDocument](text).flatMap(validateQueue)
  def writeNew(output: Path, artifacts: ReviewArtifacts): Either[String, Unit] = Try {
    validate(artifacts.queue, artifacts.split).fold(
      e => throw new IllegalArgumentException(e),
      identity
    )
    LinkExporter.ensureNew(output).fold(e => throw new IllegalArgumentException(e), identity)
    artifacts.generationBinding.foreach { binding =>
      checkBinding(binding)
      require(
        populationBinding(binding) == artifacts.queue.binding,
        "generation metadata differs from label population"
      )
    }
    Files.createDirectories(output)
    artifacts.generationBinding.foreach { binding =>
      Files.writeString(
        output.resolve("generation-binding.json"),
        write(binding, indent = 2) + "\n",
        UTF_8,
        StandardOpenOption.CREATE_NEW
      )
    }
    Files.writeString(
      output.resolve("queue.json"),
      write(artifacts.queue, indent = 2) + "\n",
      UTF_8,
      StandardOpenOption.CREATE_NEW
    )
    Files.writeString(
      output.resolve("split.json"),
      write(artifacts.split, indent = 2) + "\n",
      UTF_8,
      StandardOpenOption.CREATE_NEW
    )
    ()
  }.toEither.left.map(_.getMessage)
}

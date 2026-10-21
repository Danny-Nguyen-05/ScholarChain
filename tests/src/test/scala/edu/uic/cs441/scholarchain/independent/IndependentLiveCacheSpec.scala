package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import java.nio.file.Files
import org.scalatest.funsuite.AnyFunSuite

class IndependentLiveCacheSpec extends AnyFunSuite {
  import IndependentLiveFixtures.*
  test("fake cache cannot satisfy live request and live cache rejects fake mode") {
    val r = request()
    val root = Files.createTempDirectory("scholarchain-independent-live-isolation-").toRealPath()
    val fakeRaw = r.copy(
      requestHash = "",
      configHash = sourceConfig.fingerprint,
      promptVersion = Adjudication.promptVersion,
      promptHash = IndependentReviewFixtures.sha256(Adjudication.prompt),
      responseSchemaHash = IndependentReviewFixtures.sha256(Adjudication.schemaText),
      provider = sourceConfig.adjudication.provider,
      model = sourceConfig.adjudication.model,
      modelVersion = sourceConfig.adjudication.modelVersion,
      generationSettings = sourceConfig.adjudication.generationSettings,
      mode = "fake"
    )
    val fake = fakeRaw.copy(requestHash = StrictJson.hash(fakeRaw))
    assert(Adjudication.validateRequest(fake, sourceConfig).isRight)
    assert(AdjudicationCache.write(root, fake, response(fake), sourceConfig).isRight)
    assert(LiveAdjudicationCache.read(root, r, config).contains(None))
    val result = OpenAIResponses.parseResponse(http(envelope(r)), r, config).toOption.get
    val stored = LiveAdjudicationCache.write(root, r, result, config)
    assert(stored.isRight, stored.toString)
    assert(AdjudicationCache.read(root, fake, sourceConfig).contains(Some(response(fake))))
    assert(LiveAdjudicationCache.read(root, r, config).contains(Some(result)))
    assert(AdjudicationCache.read(root, r, sourceConfig).isLeft)
    assert(LiveAdjudicationCache.read(root, r.copy(mode = "fake"), config).isLeft)
    assert(LiveAdjudicationCache.write(root, r.copy(mode = "fake"), result, config).isLeft)
  }

  test("live cache rejects corruption and context changes cannot reuse validated results") {
    val r = request()
    val root =
      Files.createTempDirectory("scholarchain-independent-live-cache-corrupt-").toRealPath()
    val result = OpenAIResponses.parseResponse(http(envelope(r)), r, config).toOption.get
    val stored = LiveAdjudicationCache.write(root, r, result, config)
    assert(stored.isRight, stored.toString)
    val variants = Vector(
      r.copy(policyHash = "0" * 64),
      r.copy(configHash = "0" * 64),
      r.copy(promptHash = "0" * 64),
      r.copy(responseSchemaHash = "0" * 64),
      r.copy(modelVersion = "synthetic-other-version"),
      r.copy(mode = "fake"),
      r.copy(generationSettings = r.generationSettings.updated("reasoning.effort", "high"))
    )
    assert(variants.forall(v => LiveAdjudicationCache.key(v) != LiveAdjudicationCache.key(r)))
    val cache =
      root.resolve("live/openai/gpt-6-luna").resolve(LiveAdjudicationCache.key(r) + ".json")
    Files.writeString(cache, "{corrupt")
    assert(LiveAdjudicationCache.read(root, r, config).isLeft)
  }

  test(
    "invalid live results are never cached and a complete write leaves no partial readable files"
  ) {
    val r = request()
    val root = Files.createTempDirectory("scholarchain-independent-live-cache-atomic-").toRealPath()
    val result = OpenAIResponses.parseResponse(http(envelope(r)), r, config).toOption.get
    val invalid =
      result.copy(response = result.response.copy(pairId = "resolution-pair:" + "0" * 64))
    assert(LiveAdjudicationCache.write(root, r, invalid, config).isLeft)
    assert(LiveAdjudicationCache.read(root, r, config).contains(None))
    val stored = LiveAdjudicationCache.write(root, r, result, config)
    assert(stored.isRight, stored.toString)
    val entries = Files.list(root.resolve("live/openai/gpt-6-luna"))
    try {
      import scala.jdk.CollectionConverters.*
      assert(
        entries.iterator.asScala.map(_.getFileName.toString).toVector == Vector(
          LiveAdjudicationCache.key(r) + ".json"
        )
      )
    } finally entries.close()
  }
}

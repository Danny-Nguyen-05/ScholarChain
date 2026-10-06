package edu.uic.cs441.scholarchain.core

import java.nio.file.Files

import org.scalatest.funsuite.AnyFunSuite

class ConfigLoaderSpec extends AnyFunSuite {
  private val base: String =
    """{
      |  "configSchemaVersion": "scholarchain.config.v1",
      |  "application": {"environment": "fixture", "region": "fixture-region", "awsAccountId": null},
      |  "storage": {
      |    "rawBucket": "fixture-raw",
      |    "curatedBucket": "fixture-curated",
      |    "graphBucket": "fixture-graph",
      |    "ragBucket": "fixture-rag"
      |  },
      |  "neptune": {"endpoint": "fixture-neptune.example", "port": 8182, "queryTimeoutMs": 4321},
      |  "s3Vectors": {
      |    "vectorBucket": "fixture-vectors",
      |    "indexes": {
      |      "researchers": "fixture-researchers",
      |      "communities": "fixture-communities",
      |      "abstracts": "fixture-abstracts",
      |      "paths": "fixture-paths",
      |      "topicInstitutions": "fixture-topic-institutions"
      |    }
      |  },
      |  "entityResolution": {
      |    "policyVersion": "er-v1",
      |    "acceptThreshold": 0.5,
      |    "rejectThreshold": 0.25,
      |    "llmBandMin": 0.3,
      |    "llmBandMax": 0.4
      |  },
      |  "graph": {
      |    "windowStartYear": 2011,
      |    "windowEndYear": 2011,
      |    "bridgeAlgorithm": "fixture-bridge",
      |    "bridgeParameters": {"note": "fixture"}
      |  },
      |  "retrieval": {
      |    "graphLimit": 7,
      |    "vectorLimit": 5,
      |    "contextTokenBudget": 100,
      |    "fusionPolicyVersion": "fixture-fusion",
      |    "maxPathDepth": 2
      |  },
      |  "models": {
      |    "embeddingModel": "fixture-embedding",
      |    "synthesisModel": "fixture-synthesis",
      |    "verificationModel": "fixture-verification"
      |  },
      |  "operations": {
      |    "synchronousDeadlineMs": 1000,
      |    "maxWorkflowRetries": 0,
      |    "maxConcurrentLlmCalls": 1
      |  }
      |}
      |""".stripMargin

  test("literal file values load and do not invent an account id") {
    val loaded = ConfigLoader.loadText(base, Map.empty)
    assert(loaded.isRight)
    val config = loaded.toOption.get
    assert(config.storage.rawBucket == "fixture-raw")
    assert(config.application.awsAccountId.isEmpty)
    assert(config.graph.windowStartYear == 2011 && config.graph.windowEndYear == 2011)
    assert(config.graph.bridgeAlgorithm == "fixture-bridge")
    assert(config.models.embeddingModel == "fixture-embedding")
    assert(config.neptune.endpoint == "fixture-neptune.example")
  }

  test("direct environment overrides beat file literals and placeholders") {
    val withPlaceholder = base.replace("\"fixture-raw\"", "\"${RAW_BUCKET}\"")
    val env = Map(
      "RAW_BUCKET" -> "from-placeholder",
      "SCHOLARCHAIN_STORAGE_RAW_BUCKET" -> "from-env",
      "SCHOLARCHAIN_GRAPH_WINDOW_END_YEAR" -> "2014",
      "SCHOLARCHAIN_GRAPH_BRIDGE_PARAM_sampleSize" -> "4"
    )
    val loaded = ConfigLoader.loadText(withPlaceholder, env).toOption.get
    assert(loaded.storage.rawBucket == "from-env")
    assert(loaded.graph.windowEndYear == 2014)
    assert(
      loaded.graph.bridgeParameters.exists(item => item.name == "sampleSize" && item.value == "4")
    )
    assert(loaded.graph.bridgeParameters.exists(_.name == "note"))
  }

  test("placeholders fill file strings when no direct override is set") {
    val withPlaceholder = base.replace("\"fixture-embedding\"", "\"${EMBEDDING_MODEL_ID}\"")
    val loaded =
      ConfigLoader.loadText(withPlaceholder, Map("EMBEDDING_MODEL_ID" -> "fixture-model-from-env"))
    assert(loaded.toOption.get.models.embeddingModel == "fixture-model-from-env")
  }

  test("SCHOLARCHAIN_CONFIG selects the file") {
    val path = Files.createTempFile("scholarchain-config", ".json")
    Files.writeString(path, base)
    val loaded = ConfigLoader.loadConfigured(Map("SCHOLARCHAIN_CONFIG" -> path.toString))
    assert(loaded.toOption.get.storage.graphBucket == "fixture-graph")
  }

  test("missing required values, bad versions, reversed windows, and bad thresholds fail") {
    val missing = ConfigLoader.loadText(base.replace("\"fixture-raw\"", "\"\""), Map.empty)
    assert(missing.left.exists(_.text.contains("rawBucket")))
    val version = ConfigLoader.loadText(
      base.replace("scholarchain.config.v1", "scholarchain.config.v9"),
      Map.empty
    )
    assert(version.left.exists(_.text.contains("unsupported config schema")))
    val reversed = ConfigLoader.loadText(
      base.replace("\"windowEndYear\": 2011", "\"windowEndYear\": 2010"),
      Map.empty
    )
    assert(reversed.left.exists(_.text.contains("window start")))
    val threshold = ConfigLoader.loadText(
      base.replace("\"acceptThreshold\": 0.5", "\"acceptThreshold\": 1.5"),
      Map.empty
    )
    assert(threshold.left.exists(_.text.contains("thresholds")))
  }

  test("versioned JSON HOCON subset .conf and .json load through the real loader") {
    val confResource = getClass.getResource("/scholarchain.config.v1.conf")
    val fromConf = ConfigLoader.loadConfigured(Map("SCHOLARCHAIN_CONFIG" -> confResource.getPath))
    val resource = getClass.getResource("/scholarchain.config.v1.json")
    assert(resource != null)
    val loaded = ConfigLoader.loadConfigured(Map("SCHOLARCHAIN_CONFIG" -> resource.getPath))
    assert(loaded.isRight)
    assert(fromConf == loaded)
    val config = loaded.toOption.get
    assert(config.configSchemaVersion == SchemaVersions.config)
    assert(config.application.awsAccountId.isEmpty)
    assert(config.storage.rawBucket == "local-dev-raw")
    assert(config.graph.windowStartYear == 2011)
  }

  test("graph years outside 1..9999 are rejected") {
    val low = ConfigLoader.loadText(
      base
        .replace("\"windowStartYear\": 2011", "\"windowStartYear\": -1")
        .replace(
          "\"windowEndYear\": 2011",
          "\"windowEndYear\": 0"
        ),
      Map.empty
    )
    assert(low.left.exists(_.text.contains("windowStartYear")))
    val high = ConfigLoader.loadText(
      base
        .replace("\"windowStartYear\": 2011", "\"windowStartYear\": 10000")
        .replace(
          "\"windowEndYear\": 2011",
          "\"windowEndYear\": 10001"
        ),
      Map.empty
    )
    assert(high.left.exists(_.text.contains("windowEndYear")))
  }

  test("YAML and non-JSON HOCON are rejected without a vendored parser") {
    val yaml = "application:\n  environment: fixture\n"
    val rejected = ConfigLoader.loadText(yaml, Map.empty)
    assert(rejected.left.exists(_.text.contains("unsupported by this loader")))
  }
}

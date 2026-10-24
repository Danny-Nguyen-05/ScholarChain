package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.core.{CoreJson, NamedText, SchemaVersions}
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.services.neptunedata.NeptunedataClient
import software.amazon.awssdk.services.neptunedata.model.*

import scala.collection.mutable

class IndependentStorageGraphReaderSpec extends AnyFunSuite {
  import IndependentStorage7BSupport.*
  import IndependentStorageFixtures.*
  import StorageResult.*

  private val config = GraphReaderConfig(
    maxDepth = 3,
    maxLimit = 4,
    maxCursorOffset = 8,
    requestTimeoutMillis = 3500,
    retry = RetryConfig(2, 0, 0)
  )

  test(
    "all graph reader operations use allowlisted templates with values bound outside query text"
  ) {
    val calls = mutable.Buffer.empty[ExecuteOpenCypherQueryRequest]
    val client = stub(classOf[NeptunedataClient]) {
      case ("executeOpenCypherQuery", Vector(request: ExecuteOpenCypherQueryRequest)) =>
        calls += request
        ExecuteOpenCypherQueryResponse.builder().results(document(ujson.Arr())).build()
    }
    val reader: GraphReader = new NeptuneGraphReader(client, config)
    val userText = "synthetic' MATCH (secret) RETURN secret //"
    reader.node(userText)
    reader.neighbors(userText, "all-years", Set("AUTHORED"), 2, None)
    reader.directCoauthors(userText, "all-years", 2)
    reader.shortestPaths(userText, secondResearcherId, 2, "all-years", 2)
    reader.communityMembers(userText, "all-years", 2)
    reader.crossCommunityEdges(userText, "all-years", 2)
    assert(calls.size == 6)
    calls.zipWithIndex.foreach { (request, ordinal) =>
      assert(!request.openCypherQuery().contains(userText))
      assert(request.openCypherQuery().contains("$"))
      val parameters = ujson.read(request.parameters())
      if (ordinal < 4) assert(parameters.obj.values.exists(_ == ujson.Str(userText)))
      else {
        assert(parameters("membership").str.startsWith("|"))
        assert(parameters("membership").str.endsWith("|"))
      }
      assert(request.openCypherQuery().contains("TIMEOUTMILLISECONDS 3500"))
      assert(request.overrideConfiguration().isPresent)
      val timeout = request.overrideConfiguration().get().apiCallTimeout().get().toMillis
      assert(timeout > 0 && timeout <= 4500)
    }
  }

  test("depth, result, cursor and relationship bounds reject before issuing graph requests") {
    val client = stub(classOf[NeptunedataClient])(PartialFunction.empty)
    val reader: GraphReader = new NeptuneGraphReader(client, config)
    val invalid = Vector(
      reader.shortestPaths(researcherId, secondResearcherId, 0, "all-years", 1),
      reader.shortestPaths(researcherId, secondResearcherId, 4, "all-years", 1),
      reader.shortestPaths(researcherId, secondResearcherId, 2, "all-years", 5),
      reader.neighbors(researcherId, "all-years", Set("AUTHORED"), 0, None),
      reader.neighbors(researcherId, "all-years", Set("AUTHORED"), 5, None),
      reader.neighbors(researcherId, "all-years", Set("AUTHORED"), 1, Some("-1")),
      reader.neighbors(researcherId, "all-years", Set("AUTHORED"), 1, Some("9")),
      reader.neighbors(researcherId, "all-years", Set("AUTHORED"), 1, Some("malformed")),
      reader.neighbors(researcherId, "all-years", Set("AUTHORED` DELETE n //"), 1, None),
      reader.communityMembers("synthetic-community", "all-years", 5),
      reader.crossCommunityEdges("synthetic-community", "all-years", 0)
    )
    assert(invalid.forall(!StorageResult.successful(_)))
  }

  test("graph SDK failure retries to the configured bound and never exposes provider payload") {
    var calls = 0
    val client = stub(classOf[NeptunedataClient]) {
      case ("executeOpenCypherQuery", Vector(_: ExecuteOpenCypherQueryRequest)) =>
        calls += 1
        throw NeptunedataException
          .builder()
          .statusCode(503)
          .message("synthetic-sensitive-payload")
          .build()
    }
    val result = new NeptuneGraphReader(client, config).node(researcherId)
    assert(!StorageResult.successful(result))
    assert(calls == 2)
    assert(!result.toString.contains("synthetic-sensitive-payload"))
  }

  test(
    "structural SDK node response preserves raw control characters, quotes, backslashes and Unicode"
  ) {
    val label = "Synthetic α研究者\r\nsecond\t\"quoted\" \\ path 🧪"
    val property = "Source β\r\nline\t\"citation\" \\ evidence 研究"
    val node =
      researcher.copy(label = label, properties = Vector(NamedText("sourceText", property)))
    val response = document(
      ujson.Arr(
        ujson.Obj(
          "nodeId" -> node.nodeId,
          "labels" -> ujson.Arr("RESEARCHER"),
          "properties" -> ujson.Obj(
            "schemaVersion" -> SchemaVersions.domain,
            "label" -> label,
            "propertiesJson" -> CoreJson.compact(node.properties),
            "provenanceJson" -> CoreJson.compact(node.provenance)
          )
        )
      )
    )
    val client = stub(classOf[NeptunedataClient]) {
      case ("executeOpenCypherQuery", Vector(_: ExecuteOpenCypherQueryRequest)) =>
        ExecuteOpenCypherQueryResponse.builder().results(response).build()
    }
    val result = new NeptuneGraphReader(client, config).node(node.nodeId)
    assert(result == Found(node), result.toString)
    assert(
      StorageResult
        .value(result)
        .get
        .label
        .getBytes(java.nio.charset.StandardCharsets.UTF_8)
        .sameElements(label.getBytes(java.nio.charset.StandardCharsets.UTF_8))
    )
  }

  test("structural SDK neighbor edge properties preserve raw multiline text byte for byte") {
    val raw = "Evidence γ研究\r\nsecond\t\"quoted\" \\ path 🧪"
    val edge = IndependentStorageGraphFixture.edge
    val response = document(
      ujson.Arr(
        ujson.Obj(
          "nodeId" -> secondResearcherId,
          "edgeId" -> edge,
          "edgeType" -> "COAUTHORED_WITH",
          "properties" -> ujson.Obj("label" -> raw, "sourceText" -> raw),
          "communityQualificationsJson" -> ujson.Null
        )
      )
    )
    val client = stub(classOf[NeptunedataClient]) {
      case ("executeOpenCypherQuery", Vector(_: ExecuteOpenCypherQueryRequest)) =>
        ExecuteOpenCypherQueryResponse.builder().results(response).build()
    }
    val result =
      new NeptuneGraphReader(client, config).directCoauthors(researcherId, "all-years", 1)
    assert(
      result == Found(
        GraphPage(
          Vector(
            GraphNeighbor(
              secondResearcherId,
              edge,
              "COAUTHORED_WITH",
              Map("label" -> raw, "sourceText" -> raw)
            )
          ),
          None
        )
      ),
      result.toString
    )
    val actual = StorageResult.value(result).get.items.head.properties("label")
    assert(
      actual
        .getBytes(java.nio.charset.StandardCharsets.UTF_8)
        .sameElements(raw.getBytes(java.nio.charset.StandardCharsets.UTF_8))
    )
  }
}

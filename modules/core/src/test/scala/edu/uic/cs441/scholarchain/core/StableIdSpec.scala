package edu.uic.cs441.scholarchain.core

import java.util.UUID

import org.scalatest.funsuite.AnyFunSuite

class StableIdSpec extends AnyFunSuite {
  test("DOI work ids share one authoritative id across sample URL forms") {
    val expected = "work:doi:10.1007/978-3-642-31674-6_1"
    assert(StableIds.workIdFromDoi("10.1007/978-3-642-31674-6_1").contains(expected))
    assert(
      StableIds.workIdFromDoi("https://doi.org/10.1007/978-3-642-31674-6_1").contains(expected)
    )
    assert(
      StableIds.workIdFromDoi("https://doi.org/10.1007/978-3-642-31674-6_1").contains(expected)
    )
    assert(
      StableIds
        .normalizeDoi("https://dx.doi.org/10.1007/978-3-642-31674-6_1")
        .contains(Fixtures.doi)
    )
  }

  test("DOI outranks a dblp key and an OpenAlex work id when both are present") {
    val native = StableIds.workIdFromDblpKey("series/sapere/BerkeleyR13")
    val resolved = StableIds.authoritativeWorkId(Some(Fixtures.doi), None, native)
    assert(resolved.contains(Fixtures.workId))
    val openAlex = StableIds.workIdFromOpenAlex("https://openalex.org/W4254447616")
    assert(openAlex.contains("work:openalex:W4254447616"))
    val preferred = StableIds.authoritativeWorkId(
      Some("https://doi.org/10.1007/978-3-642-31674-6_1"),
      None,
      openAlex
    )
    assert(preferred.contains(Fixtures.workId))
  }

  test("provisional researcher ids are mention-scoped and are not the ORCID id") {
    assert(
      Fixtures.berkeleyResearcherId ==
        "researcher:scholarchain:identity-v1:3b92b364bf792bb6c60f4564a88a74c89e47e6305f7ec3d5e00dbdc7098a9577"
    )
    assert(
      Fixtures.riceProvisionalId ==
        "researcher:scholarchain:identity-v1:69d5a3c38c2ff7e7c3eb63a35791dd6675031e1c15807df20ac240fc47ec598f"
    )
    val sameNameOtherPaper = StableIds.provisionalResearcherId(
      Fixtures.identityPolicy,
      SourceType.Dblp,
      "series/sapere/NasutoB13",
      1,
      Fixtures.berkeleyName
    )
    assert(sameNameOtherPaper.toOption != Some(Fixtures.berkeleyResearcherId))
    val spaced = StableIds.provisionalResearcherId(
      Fixtures.identityPolicy,
      SourceType.Dblp,
      Fixtures.dblpKey,
      1,
      TextNorm.personName("Istvan   S. N. Berkeley")
    )
    assert(spaced.contains(Fixtures.berkeleyResearcherId))
    assert(Fixtures.riceOrcidResearcherId == "researcher:orcid:0000-0002-4414-6920")
    assert(Fixtures.riceProvisionalId != Fixtures.riceOrcidResearcherId)
  }

  test("OpenAlex author ids are rejected as validated researcher ids") {
    val rejected = StableIds.researcherIdFromValidatedExternal(
      "openalex-author",
      "https://openalex.org/A5101955953"
    )
    assert(rejected.left.exists(_.code == ViolationCode.UnconfirmedIdentity))
  }

  test("canonical pair order is string order and self-pairs fail") {
    val ordered = StableIds.canonicalPair(Fixtures.riceProvisionalId, Fixtures.berkeleyResearcherId)
    assert(ordered.contains((Fixtures.berkeleyResearcherId, Fixtures.riceProvisionalId)))
    assert(StableIds.canonicalPair("same", "same").isLeft)
  }

  test("coauthor edge id hashes canonical order, window, and policy") {
    assert(
      Fixtures.coauthorEdgeId ==
        "coauthor-edge:aec73376772c67c733c1b4e9d9714503f80092526376cca0b51e51edbb29bd56"
    )
    val swapped = StableIds.coauthorEdgeId(
      Fixtures.riceProvisionalId,
      Fixtures.berkeleyResearcherId,
      2011,
      2011,
      Fixtures.graphPolicy
    )
    assert(swapped.contains(Fixtures.coauthorEdgeId))
    val reversedWindow = StableIds.coauthorEdgeId(
      Fixtures.berkeleyResearcherId,
      Fixtures.riceProvisionalId,
      2012,
      2011,
      Fixtures.graphPolicy
    )
    assert(reversedWindow.left.exists(_.code == ViolationCode.ReversedTimeWindow))
  }

  test("chunk and profile ids hash entity, source version, type, ordinal, and text") {
    assert(
      Fixtures.titleChunkId == "chunk:f1ea5a3559c54d853d3e2fa4739598cc01ffae4b638adbecf2a107dfb820da7a"
    )
    assert(
      Fixtures.profileId == "profile:f339b680b8c639e41d78398212b6fb20b1abac93eb47b74f462e786c064f499c"
    )
    val withOrdinal = StableIds.chunkOrProfileId(
      Fixtures.workId,
      "dblp-2026-10-03",
      "title",
      Some(1),
      Fixtures.title
    )
    assert(withOrdinal.toOption != Some(Fixtures.titleChunkId))
  }

  test("non-text evidence ids are distinct for graph path, metric, and edge") {
    assert(
      Fixtures.graphPathEvidenceId ==
        "evidence:graph-path:cb3cd479b384bdb4e50c1014172a3251dc078cb683e2bfe49bfc0c35d48b34f7"
    )
    assert(
      Fixtures.metricEvidenceId ==
        "evidence:metric:6abb22585f7fec759e94e317a619c55beddcbd8b2db1ad3b2b0496d996297242"
    )
    assert(
      Fixtures.edgeEvidenceId ==
        "evidence:edge:05be3b0f2b2b89677e6bbafdbd206ee77be8611f90e2f78d8bb45d4292825eed"
    )
    val reversed = StableIds.nonTextEvidenceId(
      "graph-path",
      Seq(Fixtures.riceProvisionalId, Fixtures.berkeleyResearcherId)
    )
    assert(reversed.toOption != Some(Fixtures.graphPathEvidenceId))
    assert(StableIds.nonTextEvidenceId("graph-path", Seq(Fixtures.workId)).isLeft)
    assert(StableIds.parseNonTextEvidenceId(Fixtures.titleChunkId).isLeft)
    assert(StableIds.parseEvidenceId(Fixtures.titleChunkId).isRight)
    assert(StableIds.parseEvidenceId(Fixtures.graphPathEvidenceId).isRight)
    assert(StableIds.parseChunkOrProfileId(Fixtures.graphPathEvidenceId).isLeft)
  }

  test("graph edge id hashes type, canonical endpoints, policy, and evidence") {
    assert(
      Fixtures.graphEdgeId ==
        "graph-edge:719a19d4f05ff6916a7d3767cac877760d5871a7fd65af7ce24e7adecf59447a"
    )
    val directed = StableIds.graphEdgeId(
      GraphEdgeType.Authored,
      Fixtures.berkeleyMentionId,
      Fixtures.workId,
      Fixtures.graphPolicy,
      Fixtures.workId
    )
    val reversed = StableIds.graphEdgeId(
      GraphEdgeType.Authored,
      Fixtures.workId,
      Fixtures.berkeleyMentionId,
      Fixtures.graphPolicy,
      Fixtures.workId
    )
    assert(directed != reversed)
  }

  test("run ids are version-4 UUIDs and do not take a timestamp") {
    assert(Fixtures.runId == "run:00112233-4455-4677-8899-aabbccddeeff")
    val clockUuid = UUID.fromString("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    assert(clockUuid.version() == 1)
    assert(StableIds.newRunId(clockUuid).left.exists(_.code == ViolationCode.MalformedId))
    assert(StableIds.parseRunId("run:not-a-uuid").isLeft)
  }
}

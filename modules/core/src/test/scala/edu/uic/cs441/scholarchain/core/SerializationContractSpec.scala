package edu.uic.cs441.scholarchain.core

import org.scalatest.funsuite.AnyFunSuite
import upickle.default.ReadWriter

import scala.io.Source

class SerializationContractSpec extends AnyFunSuite {

  test("work record round-trips and freezes the bibliographic wire example") {
    freeze("work-record.json", Fixtures.work)(DomainValidation.check)
  }

  test("canonical researcher and match decision freeze the identity wire examples") {
    freeze("canonical-researcher.json", Fixtures.orcidResearcher)(DomainValidation.check)
    freeze("match-decision.json", Fixtures.unresolvedMatch)(DomainValidation.check)
    freeze("match-decision-conflict.json", Fixtures.conflictMatch)(DomainValidation.check)
  }

  test("collaboration records freeze pair order and the coauthor edge id") {
    freeze("publication-team.json", Fixtures.team)(value =>
      DomainValidation.check(value, Fixtures.work)
    )
    freeze("authorship-record.json", Fixtures.authorship)(value =>
      DomainValidation.check(value, Fixtures.work)
    )
    freeze("coauthor-pair-candidate.json", Fixtures.pair)(value =>
      DomainValidation.check(value, Fixtures.work)
    )
    freeze("coauthor-edge.json", Fixtures.edge)(DomainValidation.check)
    val edgeJson = CoreJson.pretty(Fixtures.edge)
    assert(edgeJson.contains(Fixtures.coauthorEdgeId))
    assert(edgeJson.contains("\"researcherA\": \"" + Fixtures.berkeleyResearcherId + "\""))
  }

  test("metrics, reference data, graph, evidence, and run manifest freeze") {
    freeze("researcher-metrics.json", Fixtures.metrics)(DomainValidation.check)
    freeze("venue.json", Fixtures.venue)(DomainValidation.check)
    freeze("institution.json", Fixtures.openAlexInstitution)(DomainValidation.check)
    freeze("topic.json", Fixtures.topic)(DomainValidation.check)
    freeze("graph-node.json", Fixtures.workNode)(DomainValidation.check)
    freeze("graph-edge.json", Fixtures.graphEdge)(DomainValidation.check)
    freeze("graph-edge-orcid-employment.json", Fixtures.orcidEmploymentEdge)(DomainValidation.check)
    freeze("evidence-item.json", Fixtures.evidence)(DomainValidation.check)
    freeze("evidence-item-graph-path.json", Fixtures.graphPathEvidence)(DomainValidation.check)
    freeze("evidence-item-metric.json", Fixtures.metricEvidence)(DomainValidation.check)
    freeze("evidence-item-edge.json", Fixtures.edgeEvidence)(DomainValidation.check)
    freeze("evidence-bundle.json", Fixtures.bundle)(DomainValidation.check)
    freeze("query-plan.json", Fixtures.plan)(DomainValidation.check)
    freeze("answer-claim.json", Fixtures.claim)(DomainValidation.check)
    freeze("answer-claim-graph-path.json", Fixtures.graphPathClaim)(DomainValidation.check)
    freeze("answer-response.json", Fixtures.response)(DomainValidation.check)
    freeze("run-manifest.json", Fixtures.manifest)(DomainValidation.check)
  }

  test("author mention wire example states that a name is not an identity") {
    freeze("author-mention.json", Fixtures.berkeleyMention)(DomainValidation.check)
    val json = CoreJson.pretty(Fixtures.berkeleyMention)
    assert(json.contains("NAME_ONLY_UNCONFIRMED"))
    assert(json.contains("not a confirmed researcher identity"))
  }

  private def freeze[T: ReadWriter](name: String, value: T)(
      validate: T => Either[Vector[DomainViolation], T]
  ): Unit = {
    val checked = validate(value)
    assert(checked.isRight, checked.left.toOption.map(_.mkString("; ")).getOrElse(""))
    val pretty = CoreJson.pretty(value) + "\n"
    val resource = Option(getClass.getClassLoader.getResourceAsStream(s"wire/$name"))
      .getOrElse(fail(s"missing frozen wire example wire/$name"))
    val frozen = Source.fromInputStream(resource, "UTF-8").mkString
    assert(frozen == pretty, s"wire example drifted: $name")
    val parsed = CoreJson.parseAndValidate(pretty.trim)(validate)
    assert(parsed.isRight, parsed.left.toOption.map(_.mkString("; ")).getOrElse(""))
    assert(CoreJson.pretty(parsed.toOption.get) + "\n" == pretty)
  }
}

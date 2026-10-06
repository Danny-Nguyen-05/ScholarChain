package edu.uic.cs441.scholarchain.core

import upickle.core.Abort
import upickle.default.{ReadWriter, readwriter}

/** Source systems in the committed portfolio, plus ScholarChain for derived records. */
enum SourceType(val wire: String) {
  case Dblp extends SourceType("DBLP")
  case OpenAlex extends SourceType("OPENALEX")
  case Orcid extends SourceType("ORCID")
  case Crossref extends SourceType("CROSSREF")
  case ScholarChain extends SourceType("SCHOLARCHAIN")
}

object SourceType {
  given ReadWriter[SourceType] = EnumCodecs.wire(SourceType.values, _.wire)
}

/** Alignment result. `UNRESOLVED` means no decision was produced. `CONFLICT` means the compared
  * records disagree and must stay unmerged.
  */
enum MatchOutcome(val wire: String) {
  case Accepted extends MatchOutcome("ACCEPTED")
  case Rejected extends MatchOutcome("REJECTED")
  case Unresolved extends MatchOutcome("UNRESOLVED")
  case Conflict extends MatchOutcome("CONFLICT")
}

object MatchOutcome {
  given ReadWriter[MatchOutcome] = EnumCodecs.wire(MatchOutcome.values, _.wire)
}

enum EvidenceType(val wire: String) {
  case WorkMetadata extends EvidenceType("WORK_METADATA")
  case AuthorMention extends EvidenceType("AUTHOR_MENTION")
  case ResearcherProfile extends EvidenceType("RESEARCHER_PROFILE")
  case CoauthorEdge extends EvidenceType("COAUTHOR_EDGE")
  case Metric extends EvidenceType("METRIC")
  case GraphPath extends EvidenceType("GRAPH_PATH")
  case Institution extends EvidenceType("INSTITUTION")
  case Topic extends EvidenceType("TOPIC")
  case Venue extends EvidenceType("VENUE")
  case TextChunk extends EvidenceType("TEXT_CHUNK")
}

object EvidenceType {
  given ReadWriter[EvidenceType] = EnumCodecs.wire(EvidenceType.values, _.wire)
}

enum CollaborationMetric(val wire: String) {
  case PublicationCount extends CollaborationMetric("PUBLICATION_COUNT")
  case DistinctCoauthorCount extends CollaborationMetric("DISTINCT_COAUTHOR_COUNT")
  case TotalCoauthorOccurrences extends CollaborationMetric("TOTAL_COAUTHOR_OCCURRENCES")
  case AverageCoauthorsPerPaper extends CollaborationMetric("AVERAGE_COAUTHORS_PER_PAPER")
  case MaximumCoauthorsOnOnePaper extends CollaborationMetric("MAXIMUM_COAUTHORS_ON_ONE_PAPER")
  case WeightedDegree extends CollaborationMetric("WEIGHTED_DEGREE")
  case BridgeScore extends CollaborationMetric("BRIDGE_SCORE")
  case Coreness extends CollaborationMetric("CORENESS")
}

object CollaborationMetric {
  given ReadWriter[CollaborationMetric] = EnumCodecs.wire(CollaborationMetric.values, _.wire)
}

enum QueryOperation(val wire: String) {
  case ResearcherRanking extends QueryOperation("RESEARCHER_RANKING")
  case MaximumTeamSize extends QueryOperation("MAXIMUM_TEAM_SIZE")
  case DirectCoauthors extends QueryOperation("DIRECT_COAUTHORS")
  case ShortestPath extends QueryOperation("SHORTEST_PATH")
  case ComponentLookup extends QueryOperation("COMPONENT_LOOKUP")
  case CommunityComparison extends QueryOperation("COMMUNITY_COMPARISON")
  case BridgeRanking extends QueryOperation("BRIDGE_RANKING")
  case TemporalComparison extends QueryOperation("TEMPORAL_COMPARISON")
  case TopicFilter extends QueryOperation("TOPIC_FILTER")
  case InstitutionFilter extends QueryOperation("INSTITUTION_FILTER")
  case SemanticExplanation extends QueryOperation("SEMANTIC_EXPLANATION")
}

object QueryOperation {
  given ReadWriter[QueryOperation] = EnumCodecs.wire(QueryOperation.values, _.wire)
}

enum VerificationStatus(val wire: String) {
  case Verified extends VerificationStatus("VERIFIED")
  case Rejected extends VerificationStatus("REJECTED")
  case PartiallyVerified extends VerificationStatus("PARTIALLY_VERIFIED")
  case Abstained extends VerificationStatus("ABSTAINED")
  case Unverified extends VerificationStatus("UNVERIFIED")
}

object VerificationStatus {
  given ReadWriter[VerificationStatus] = EnumCodecs.wire(VerificationStatus.values, _.wire)
}

enum GraphNodeClass(val wire: String) {
  case Researcher extends GraphNodeClass("RESEARCHER")
  case AuthorMention extends GraphNodeClass("AUTHOR_MENTION")
  case Work extends GraphNodeClass("WORK")
  case Venue extends GraphNodeClass("VENUE")
  case Institution extends GraphNodeClass("INSTITUTION")
  case Topic extends GraphNodeClass("TOPIC")
  case TextChunk extends GraphNodeClass("TEXT_CHUNK")
  case DatasetSnapshot extends GraphNodeClass("DATASET_SNAPSHOT")
}

object GraphNodeClass {
  given ReadWriter[GraphNodeClass] = EnumCodecs.wire(GraphNodeClass.values, _.wire)
}

enum GraphEdgeType(val wire: String) {
  case Authored extends GraphEdgeType("AUTHORED")
  case ResolvesTo extends GraphEdgeType("RESOLVES_TO")
  case CoauthoredWith extends GraphEdgeType("COAUTHORED_WITH")
  case PublishedIn extends GraphEdgeType("PUBLISHED_IN")
  case AffiliatedWith extends GraphEdgeType("AFFILIATED_WITH")
  case HasTopic extends GraphEdgeType("HAS_TOPIC")
  case DerivedFrom extends GraphEdgeType("DERIVED_FROM")
  case SupportedBy extends GraphEdgeType("SUPPORTED_BY")
}

object GraphEdgeType {
  val undirected: Set[GraphEdgeType] = Set(GraphEdgeType.CoauthoredWith)

  def isUndirected(edgeType: GraphEdgeType): Boolean = undirected.contains(edgeType)

  given ReadWriter[GraphEdgeType] = EnumCodecs.wire(GraphEdgeType.values, _.wire)
}

/** An author string is not a confirmed researcher. Status records how far identification went. */
enum MentionIdentityStatus(val wire: String) {
  case NameOnlyUnconfirmed extends MentionIdentityStatus("NAME_ONLY_UNCONFIRMED")
  case ExternalIdentifierObserved extends MentionIdentityStatus("EXTERNAL_IDENTIFIER_OBSERVED")
  case ResolvedToResearcher extends MentionIdentityStatus("RESOLVED_TO_RESEARCHER")
}

object MentionIdentityStatus {
  given ReadWriter[MentionIdentityStatus] =
    EnumCodecs.wire(MentionIdentityStatus.values, _.wire)
}

enum IdentifierInterpretation(val wire: String) {
  case ValidatedExternal extends IdentifierInterpretation("VALIDATED_EXTERNAL")
  case DisambiguationHypothesis extends IdentifierInterpretation("DISAMBIGUATION_HYPOTHESIS")
  case SourceObservation extends IdentifierInterpretation("SOURCE_OBSERVATION")
}

object IdentifierInterpretation {
  given ReadWriter[IdentifierInterpretation] =
    EnumCodecs.wire(IdentifierInterpretation.values, _.wire)
}

private object EnumCodecs {
  def wire[T](values: Array[T], asWire: T => String): ReadWriter[T] = {
    val lookup = values.iterator.map(value => asWire(value) -> value).toMap
    readwriter[String].bimap(
      asWire,
      text =>
        lookup.getOrElse(
          text,
          throw Abort(s"unsupported value: $text")
        )
    )
  }
}

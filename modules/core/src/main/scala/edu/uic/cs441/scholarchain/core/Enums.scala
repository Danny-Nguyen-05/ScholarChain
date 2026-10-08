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

/** Hadoop preparation stage that produced a [[RejectRecord]]. */
enum PreparationStage(val wire: String) {
  case Parse extends PreparationStage("PARSE")
  case Normalize extends PreparationStage("NORMALIZE")
  case IdentifierIndex extends PreparationStage("IDENTIFIER_INDEX")
  case Block extends PreparationStage("BLOCK")
  case MatchCandidate extends PreparationStage("MATCH_CANDIDATE")
  case PublicationTeam extends PreparationStage("PUBLICATION_TEAM")
  case Authorship extends PreparationStage("AUTHORSHIP")
  case CoauthorPair extends PreparationStage("COAUTHOR_PAIR")
  case Export extends PreparationStage("EXPORT")
}

object PreparationStage {
  given ReadWriter[PreparationStage] = EnumCodecs.wire(PreparationStage.values, _.wire)
}

/** Closed reasons a valid domain record was not emitted. Duplicate and conflicting observations are
  * different codes.
  */
enum RejectReasonCode(val wire: String) {
  case MalformedRecord extends RejectReasonCode("MALFORMED_RECORD")
  case UnsupportedRecordType extends RejectReasonCode("UNSUPPORTED_RECORD_TYPE")
  case InvalidIdentifier extends RejectReasonCode("INVALID_IDENTIFIER")
  case MissingRequiredField extends RejectReasonCode("MISSING_REQUIRED_FIELD")
  case OversizeRecord extends RejectReasonCode("OVERSIZE_RECORD")
  case OversizeXmlEntityExpansion extends RejectReasonCode("OVERSIZE_XML_ENTITY_EXPANSION")
  case UnsafeEntity extends RejectReasonCode("UNSAFE_ENTITY")
  case OversizeBlock extends RejectReasonCode("OVERSIZE_BLOCK")
  case OversizeCandidatePairs extends RejectReasonCode("OVERSIZE_CANDIDATE_PAIRS")
  case OversizeTeam extends RejectReasonCode("OVERSIZE_TEAM")
  case SchemaFailure extends RejectReasonCode("SCHEMA_FAILURE")
  case ConflictingObservation extends RejectReasonCode("CONFLICTING_OBSERVATION")
  case DuplicateIdenticalObservation extends RejectReasonCode("DUPLICATE_IDENTICAL_OBSERVATION")
  case ProvenanceMismatch extends RejectReasonCode("PROVENANCE_MISMATCH")
}

object RejectReasonCode {
  given ReadWriter[RejectReasonCode] = EnumCodecs.wire(RejectReasonCode.values, _.wire)
}

/** Namespace of one indexed identifier. Work namespaces can yield a preferred work id. ORCID, ROR,
  * Ringgold, OpenAlex author ids, and OpenAlex institution ids stay non-authoritative observations.
  */
enum IdentifierNamespace(val wire: String) {
  case Doi extends IdentifierNamespace("doi")
  case Arxiv extends IdentifierNamespace("arxiv")
  case Dblp extends IdentifierNamespace("dblp")
  case OpenAlexWork extends IdentifierNamespace("openalex-work")
  case OpenAlexAuthor extends IdentifierNamespace("openalex-author")
  case Orcid extends IdentifierNamespace("orcid")
  case Ror extends IdentifierNamespace("ror")
  case Ringgold extends IdentifierNamespace("ringgold")
  case OpenAlexInstitution extends IdentifierNamespace("openalex-institution")
}

object IdentifierNamespace {
  val workNamespaces: Set[IdentifierNamespace] = Set(
    IdentifierNamespace.Doi,
    IdentifierNamespace.Arxiv,
    IdentifierNamespace.Dblp,
    IdentifierNamespace.OpenAlexWork
  )

  def authorizesWorkId(namespace: IdentifierNamespace): Boolean =
    workNamespaces.contains(namespace)

  given ReadWriter[IdentifierNamespace] = EnumCodecs.wire(IdentifierNamespace.values, _.wire)
}

/** ORCID activity path segment. These are researcher activities, not ScholarChain publications. */
enum OrcidActivityKind(val wire: String) {
  case Employment extends OrcidActivityKind("employment")
  case Education extends OrcidActivityKind("education")
  case Work extends OrcidActivityKind("work")
  case Funding extends OrcidActivityKind("funding")
  case PeerReview extends OrcidActivityKind("peer-review")
  case ResearchResource extends OrcidActivityKind("research-resource")
  case Qualification extends OrcidActivityKind("qualification")
  case Membership extends OrcidActivityKind("membership")
  case Service extends OrcidActivityKind("service")
  case Distinction extends OrcidActivityKind("distinction")
  case InvitedPosition extends OrcidActivityKind("invited-position")
}

object OrcidActivityKind {
  given ReadWriter[OrcidActivityKind] = EnumCodecs.wire(OrcidActivityKind.values, _.wire)
}

/** Hadoop preparation launch mode. There is no compiled-in default: a missing JSON field fails
  * [[HadoopPrepConfigLoader]]. `local` may use LocalJobRunner. `cluster` must not set
  * `mapreduce.framework.name` to `local`.
  */
enum HadoopExecutionMode(val wire: String) {
  case Local extends HadoopExecutionMode("local")
  case Cluster extends HadoopExecutionMode("cluster")
}

object HadoopExecutionMode {
  val wires: Set[String] = values.map(_.wire).toSet

  given ReadWriter[HadoopExecutionMode] = EnumCodecs.wire(HadoopExecutionMode.values, _.wire)
}

/** Enrichment target that can be validated without an identity decision. */
enum EnrichmentTargetKind(val wire: String) {
  case Venue extends EnrichmentTargetKind("VENUE")
  case Institution extends EnrichmentTargetKind("INSTITUTION")
  case Topic extends EnrichmentTargetKind("TOPIC")
}

object EnrichmentTargetKind {
  given ReadWriter[EnrichmentTargetKind] =
    EnumCodecs.wire(EnrichmentTargetKind.values, _.wire)
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

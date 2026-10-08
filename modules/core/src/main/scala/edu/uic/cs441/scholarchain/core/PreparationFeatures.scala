package edu.uic.cs441.scholarchain.core

/** Bibliographic feature catalog for [[MatchCandidate]].
  *
  * `prep-features-v1` stays a valid policy version. Its feature names are only the generic rules:
  * distinct, sorted, finite, and not a [[MatchOutcome]] wire name.
  *
  * `prep-features-v2` uses [[names]]. [[DomainValidation]] requires every v2 feature name to belong
  * to that closed set. Names stay distinct and sorted, values stay finite, and a name still cannot
  * be a [[MatchOutcome]] wire name. A v2 vector may contain a sorted selection of the catalog; it
  * must not contain any other name.
  *
  * Intended numeric encoding, which validation does not range-check beyond finiteness:
  *   - `exact_shared_identifier` is 1 when the block is an exact shared identifier, otherwise 0.
  *   - `same_work_id` is 1 only when both observations already have the same validated work id.
  *     That flag is not a merge.
  *   - `year_abs_delta` is -1 when either year is absent.
  *   - equality features are 1 or 0. Count features are non-negative counts.
  *
  * Block keys are not a new type. Hadoop emits one of [[blockKeyGrammars]]. Each key must also
  * satisfy the existing [[StableIds]] block-key rules: trimmed, no CR or LF, and length at most
  * 512. A `fallback:` key names one observation. It must not by itself pair unrelated records.
  */
object PreparationFeatures {
  val policyV1: String = "prep-features-v1"
  val policyV2: String = "prep-features-v2"

  val blockSize: String = "block_size"
  val exactSharedIdentifier: String = "exact_shared_identifier"
  val sameWorkId: String = "same_work_id"
  val titleEqual: String = "title_equal"
  val yearEqual: String = "year_equal"
  val yearAbsDelta: String = "year_abs_delta"
  val venueEqual: String = "venue_equal"
  val sharedAuthorNameCount: String = "shared_author_name_count"
  val sharedAuthorInitialCount: String = "shared_author_initial_count"
  val sharedAffiliationNameCount: String = "shared_affiliation_name_count"
  val sharedCoauthorNameCount: String = "shared_coauthor_name_count"

  /** Closed catalog for [[policyV2]], already in `String` sort order and free of duplicates. */
  val names: Vector[String] = Vector(
    blockSize,
    exactSharedIdentifier,
    sameWorkId,
    sharedAffiliationNameCount,
    sharedAuthorInitialCount,
    sharedAuthorNameCount,
    sharedCoauthorNameCount,
    titleEqual,
    venueEqual,
    yearAbsDelta,
    yearEqual
  )

  val nameSet: Set[String] = names.toSet

  /** Grammars Hadoop emits. Placeholders are segments, not a parser type. The year segment of
    * `title-year` is the decimal year, or `unknown` when the year is absent.
    */
  val blockKeyGrammars: Vector[String] = Vector(
    "exact:{namespace}:{value}",
    "name:{normalized}",
    "initial:{normalized}",
    "title-year:{normalizedTitle}:{year-or-unknown}",
    "venue:{normalized}",
    "affiliation:{normalized}",
    "coauthor:{normalized}",
    "fallback:{sourceWire}:{sourceRecordId}"
  )
}

package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.net.URI
import java.text.Normalizer
import java.util.Locale
import scala.util.Try
import upickle.default.ReadWriter

object Normalization {
  val version = "er-normalization-v1"

  /** NFKC retains accents; comparison-fold is separate and never changes source evidence. */
  def text(raw: String): String = Normalizer
    .normalize(raw, Normalizer.Form.NFKC)
    .replaceAll("<[^>]*>", " ")
    .toLowerCase(Locale.ROOT)
    .replaceAll("[^\\p{L}\\p{N}]+", " ")
    .trim
    .replaceAll("\\s+", " ")
  def folded(raw: String): String =
    Normalizer.normalize(text(raw), Normalizer.Form.NFD).replaceAll("\\p{M}", "")
  def nameTokens(raw: String): Vector[String] = folded(raw).split(" ").filter(_.nonEmpty).toVector
  def nameVariants(raw: String): Set[String] = {
    val tokens = nameTokens(raw)
    Set(tokens.mkString(" "), tokens.sorted.mkString(" "))
  }
  def initials(raw: String): String = nameTokens(raw).map(_.head).mkString
  def initialsCompatible(a: String, b: String): Option[Double] = {
    def ordered(raw: String): Vector[String] = {
      val parts = raw.split(",", -1);
      if (parts.length == 2) nameTokens(parts(1)) ++ nameTokens(parts(0)) else nameTokens(raw)
    }
    val x = ordered(a); val y = ordered(b)
    if (x.size < 2 || y.size < 2) None
    else
      Some(
        if (x.last == y.last && x.dropRight(1).map(_.head) == y.dropRight(1).map(_.head)) 1.0
        else 0.0
      )
  }
  def similarity(a: String, b: String): Option[Double] = jaccard(
    text(a).split(" ").filter(_.nonEmpty).toSet,
    text(b).split(" ").filter(_.nonEmpty).toSet
  )
  def jaccard(a: Set[String], b: Set[String]): Option[Double] =
    if (a.isEmpty || b.isEmpty) None else Some(a.intersect(b).size.toDouble / a.union(b).size)
}

final case class IdentifierEvidence(
    namespace: String,
    raw: String,
    normalized: Option[String],
    normalizationVersion: String,
    role: String,
    authority: Boolean,
    evidenceRefs: Vector[String],
    error: Option[String]
) derives ReadWriter

object IdentifierRules {
  val namespaces: Set[String] = Set(
    "doi",
    "arxiv",
    "orcid",
    "openalex-work",
    "openalex-author",
    "semantic-scholar-work",
    "semantic-scholar-author",
    "repository-url"
  )
  def normalize(namespace: String, raw: String): Either[String, String] = {
    def core(ns: IdentifierNamespace) =
      StableIds.normalizeIndexedIdentifier(ns, raw).left.map(_.message)
    namespace match {
      case "doi" => core(IdentifierNamespace.Doi)
      case "arxiv" =>
        core(IdentifierNamespace.Arxiv)
          .orElse(StableIds.arxivFromSourceUri(Some(raw)).toRight("invalid arXiv identifier"))
          .map(_.stripPrefix("work:arxiv:"))
      case "orcid"           => core(IdentifierNamespace.Orcid)
      case "openalex-work"   => core(IdentifierNamespace.OpenAlexWork)
      case "openalex-author" => core(IdentifierNamespace.OpenAlexAuthor)
      case "semantic-scholar-work" =>
        val token = raw.trim.replaceFirst(
          "(?i)^https://(?:www\\.)?semanticscholar\\.org/paper/(?:[^/]+/)?",
          ""
        )
        Either.cond(
          token.matches("[0-9a-fA-F]{40}"),
          token.toLowerCase(Locale.ROOT),
          "invalid Semantic Scholar work identifier"
        )
      case "semantic-scholar-author" =>
        val token = raw.trim.replaceFirst(
          "(?i)^https://(?:www\\.)?semanticscholar\\.org/author/(?:[^/]+/)?",
          ""
        )
        Either.cond(
          token.matches("[1-9][0-9]*"),
          token,
          "invalid Semantic Scholar author identifier"
        )
      case "repository-url" =>
        Try {
          val u = new URI(raw.trim)
          require(
            Set("http", "https").contains(
              Option(u.getScheme).getOrElse("").toLowerCase(Locale.ROOT)
            ) && u.getHost != null && u.getUserInfo == null && u.getFragment == null,
            "invalid repository URL"
          )
          // Preserve path case, escaping, slash and query. No redirects or URL fetches.
          val port =
            if (
              (u.getScheme.equalsIgnoreCase("https") && u.getPort == 443) || (u.getScheme
                .equalsIgnoreCase("http") && u.getPort == 80)
            ) -1
            else u.getPort
          val authority = u.getHost.toLowerCase(Locale.ROOT) + (if (port == -1) "" else ":" + port)
          u.getScheme.toLowerCase(Locale.ROOT) + "://" + authority + Option(u.getRawPath).getOrElse(
            ""
          ) + Option(u.getRawQuery).map("?" + _).getOrElse("")
        }.toEither.left.map(_.getMessage)
      case _ => Left("unknown identifier namespace")
    }
  }
  def role(namespace: String): Option[String] = namespace.trim.toLowerCase(Locale.ROOT) match {
    case "doi" | "openalex.doi" | "openalex.ids.doi" => Some("doi")
    case "arxiv"                                     => Some("arxiv")
    case "orcid"                                     => Some("orcid")
    case "openalex" | "openalex-work" | "openalex.id" | "openalex.ids.openalex" =>
      Some("openalex-work")
    case "openalex-author"                            => Some("openalex-author")
    case "semantic-scholar" | "semantic-scholar-work" => Some("semantic-scholar-work")
    case "semantic-scholar-author"                    => Some("semantic-scholar-author")
    case "repository-url"                             => Some("repository-url")
    case _                                            => None
  }
}

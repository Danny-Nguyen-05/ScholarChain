package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.StableIds
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path, StandardCopyOption, StandardOpenOption}
import java.util.UUID
import scala.util.Try
import upickle.default.{ReadWriter, write}

final case class CachedAdjudication(
    schemaVersion: String,
    cacheKey: String,
    request: AdjudicationRequest,
    response: AdjudicationResponse,
    responseHash: String
) derives ReadWriter
object AdjudicationCache {
  def key(request: AdjudicationRequest): String = StrictJson.hash(request)
  private def location(dir: Path, request: AdjudicationRequest): Path =
    dir.resolve("fake").resolve(key(request) + ".json")
  private def safe(dir: Path): Unit = {
    val absolute = dir.toAbsolutePath.normalize
    var p: Path = absolute
    while (p != null) {
      require(!Files.isSymbolicLink(p), "symlink in cache path"); p = p.getParent
    }
    if (Files.exists(absolute)) require(Files.isDirectory(absolute), "cache directory required")
  }
  def read(
      dir: Path,
      request: AdjudicationRequest,
      config: ResolutionConfig
  ): Either[String, Option[AdjudicationResponse]] = Try {
    safe(dir); require(request.mode == "fake", "5B cache only supports fake mode")
    val path = location(dir, request); safe(path.getParent)
    if (!Files.exists(path)) None
    else {
      val text = StrictJson
        .file(
          path,
          config.adjudication.maxRequestBytes.toLong + config.adjudication.maxResponseBytes + 16384
        )
        .fold(e => throw new IllegalArgumentException(e), identity)
      val c = StrictJson
        .parse[CachedAdjudication](text)
        .fold(e => throw new IllegalArgumentException(e), identity)
      require(
        c.schemaVersion == "scholarchain.adjudication-cache.v1" && c.cacheKey == key(
          request
        ) && c.request == request && c.responseHash == StrictJson.hash(c.response),
        "cache identity/hash mismatch"
      )
      Some(
        Adjudication
          .validateResponse(upickle.default.write(c.response), request, config)
          .fold(e => throw new IllegalArgumentException(e), identity)
      )
    }
  }.toEither.left.map(_.getMessage)
  def write(
      dir: Path,
      request: AdjudicationRequest,
      response: AdjudicationResponse,
      config: ResolutionConfig
  ): Either[String, Unit] = Try {
    safe(dir); require(request.mode == "fake", "5B cache only supports fake mode")
    Adjudication
      .validateResponse(upickle.default.write(response), request, config)
      .fold(e => throw new IllegalArgumentException(e), identity)
    val path = location(dir, request); Files.createDirectories(path.getParent)
    require(!Files.isSymbolicLink(path.getParent), "symlink in cache mode directory")
    if (Files.exists(path))
      require(
        read(dir, request, config).contains(Some(response)),
        "existing cache entry differs or is corrupt"
      )
    else {
      val temp = path.resolveSibling(path.getFileName.toString + ".partial-" + UUID.randomUUID())
      val data = upickle.default.write(
        CachedAdjudication(
          "scholarchain.adjudication-cache.v1",
          key(request),
          request,
          response,
          StrictJson.hash(response)
        )
      )
      Files.writeString(temp, data, UTF_8, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)
      Files.move(temp, path, StandardCopyOption.ATOMIC_MOVE)
    }
    ()
  }.toEither.left.map(_.getMessage)
}

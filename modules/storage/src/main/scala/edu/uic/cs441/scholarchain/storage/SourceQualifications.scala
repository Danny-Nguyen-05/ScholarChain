package edu.uic.cs441.scholarchain.storage

import java.nio.charset.StandardCharsets.UTF_8
import StorageResult.*

/** Full run qualifications are immutable ordinary-S3 artifacts; cache rows retain one pointer. */
object SourceQualifications {
  def put(
      runId: String,
      json: String,
      objects: ObjectStore,
      registry: ArtifactRegistry
  ): StorageResult[SourceRunPointer] = {
    try ujson.read(json)
    catch { case _: Exception => return Rejected("invalid-source-qualifications") }
    val bytes = json.getBytes(UTF_8).toVector; val hash = StorageKeys.sha256(bytes)
    val key = StorageKeys.versioned(
      "source-qualifications",
      hash,
      StorageKeys.sha256(runId.getBytes(UTF_8).toVector) + ".json"
    )
    RowCodec.map(objects.put(key, bytes, "application/json", Map("run-id" -> runId))) { _ =>
      RowCodec.map(registry.register("source-run:" + runId, hash, key, hash))(_ =>
        Found(SourceRunPointer(runId, key, hash))
      )
    }
  }
  def get(
      pointer: SourceRunPointer,
      objects: ObjectStore,
      registry: ArtifactRegistry
  ): StorageResult[String] =
    RowCodec.map(registry.get("source-run:" + pointer.runId, pointer.sha256)) { record =>
      if (record.uri != pointer.key || record.hash != pointer.sha256)
        Rejected("source-pointer-conflict")
      else
        RowCodec.map(objects.get(pointer.key)) { obj =>
          if (obj.head.sha256 != pointer.sha256 || StorageKeys.sha256(obj.bytes) != pointer.sha256)
            Rejected("source-qualifications-hash-mismatch")
          else Found(new String(obj.bytes.toArray, UTF_8))
        }
    }
}

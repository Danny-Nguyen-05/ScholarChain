package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import upickle.default.ReadWriter
import java.nio.charset.StandardCharsets.UTF_8
import StorageResult.*

private[storage] final case class EvidencePointer(
    evidenceId: String,
    sha256: String,
    inlineJson: Option[String],
    objectKey: Option[String]
) derives ReadWriter
private[storage] class RowEvidence(
    rows: StorageRows,
    table: String,
    objects: ObjectStore,
    inlineLimit: Int
) extends EvidenceBundleStore {
  private val typed = new TypedRows[EvidencePointer](rows, table)
  def put(bundle: EvidenceBundle): StorageResult[EvidenceBundle] = {
    if (DomainValidation.check(bundle).isLeft) return Rejected("invalid-evidence-bundle")
    val json = CoreJson.compact(bundle)
    val bytes = json.getBytes(UTF_8).toVector
    val hash = StorageKeys.sha256(bytes)
    val pointer =
      if (bytes.size <= inlineLimit) EvidencePointer(bundle.bundleId, hash, Some(json), None)
      else {
        val key = StorageKeys.versioned(
          "evidence",
          hash,
          StorageKeys.sha256(bundle.bundleId.getBytes(UTF_8).toVector) + ".json"
        )
        val upload = objects.put(key, bytes, "application/json", Map.empty)
        if (!StorageResult.successful(upload))
          return RowCodec.map(upload)(_ => Rejected("evidence-upload-failed"))
        EvidencePointer(bundle.bundleId, hash, None, Some(key))
      }
    typed.put(RowKey(bundle.bundleId, "BUNDLE"), pointer) match {
      case Written(_)             => Written(bundle)
      case Unchanged(_)           => Unchanged(bundle)
      case Retried(n, Written(_)) => Retried(n, Written(bundle))
      case r                      => RowCodec.map(r)(_ => Rejected("evidence-write-failed"))
    }
  }
  def get(id: String): StorageResult[EvidenceBundle] =
    RowCodec.map(typed.get(RowKey(id, "BUNDLE"))) { pointer =>
      if (
        pointer.evidenceId != id || !pointer.sha256.matches(
          "[0-9a-f]{64}"
        ) || pointer.inlineJson.isDefined == pointer.objectKey.isDefined
      ) Rejected("corrupt-evidence-pointer")
      else {
        val bytes: StorageResult[Vector[Byte]] = pointer.inlineJson match {
          case Some(json) => Found(json.getBytes(UTF_8).toVector)
          case None       => RowCodec.map(objects.get(pointer.objectKey.get))(o => Found(o.bytes))
        }
        RowCodec.map(bytes) { b =>
          if (StorageKeys.sha256(b) != pointer.sha256) Rejected("content-hash-mismatch")
          else
            CoreJson.parse[EvidenceBundle](new String(b.toArray, UTF_8)) match {
              case Right(bundle)
                  if bundle.bundleId == id && DomainValidation.check(bundle).isRight =>
                Found(bundle)
              case _ => Rejected("corrupt-evidence-bundle")
            }
        }
      }
    }
}

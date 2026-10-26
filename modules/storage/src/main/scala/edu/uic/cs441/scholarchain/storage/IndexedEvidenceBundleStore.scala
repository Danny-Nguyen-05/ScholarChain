package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import upickle.default.ReadWriter
import StorageResult.*

private[storage] final case class EvidenceItemPointer(
    evidenceId: String,
    bundleId: String,
    itemSha256: String
) derives ReadWriter

/** Adds an immutable item-ID index in the existing ordinary object store. No new table or GSI.
  * Bundle publication precedes index publication: interrupted writes fail closed and a retry
  * repairs missing pointers. A previously published identical item may be shared across bundles;
  * its first immutable pointer remains authoritative. This is not a cross-store transaction.
  */
final class IndexedEvidenceBundleStore(
    bundles: EvidenceBundleStore,
    objects: ObjectStore,
    indexPrefix: String,
    maxPointerBytes: Int = 16384
) extends EvidenceBundleStore {
  require(indexPrefix.nonEmpty && !indexPrefix.split('/').contains("..") && maxPointerBytes > 0)

  private def key(id: String): String = StorageKeys.versioned(
    indexPrefix,
    "item-index-v1",
    StableIds.sha256Hex(id) + ".json"
  )
  private def hash(item: EvidenceItem): String = StableIds.sha256Hex(CoreJson.compact(item))
  private def pointer(id: String): StorageResult[EvidenceItemPointer] =
    RowCodec.map(objects.get(key(id))) { stored =>
      if (
        stored.bytes.size > maxPointerBytes || stored.head.key != key(id) ||
        stored.head.size != stored.bytes.size ||
        StorageKeys.sha256(stored.bytes) != stored.head.sha256
      ) Rejected("corrupt-evidence-item-pointer")
      else
        CoreJson.parse[EvidenceItemPointer](new String(stored.bytes.toArray, UTF_8)) match {
          case Right(p)
              if p.evidenceId == id && p.bundleId.nonEmpty && p.itemSha256
                .matches("[0-9a-f]{64}") =>
            Found(p)
          case _ => Rejected("corrupt-evidence-item-pointer")
        }
    }

  def get(id: String): StorageResult[EvidenceBundle] = bundles.get(id)

  override def getItem(id: String): StorageResult[EvidenceItem] =
    if (id.isEmpty) Rejected("invalid-evidence-item-id")
    else
      RowCodec.map(pointer(id)) { p =>
        bundles.get(p.bundleId) match {
          case Missing => Rejected("evidence-item-bundle-missing")
          case result =>
            RowCodec.map(result) { bundle =>
              val items = bundle.items.filter(_.evidenceId == id)
              if (
                bundle.bundleId != p.bundleId || items.size != 1 ||
                hash(items.head) != p.itemSha256
              ) Rejected("evidence-item-content-mismatch")
              else Found(items.head)
            }
        }
      }

  def put(bundle: EvidenceBundle): StorageResult[EvidenceBundle] = synchronized {
    if (
      DomainValidation.check(bundle).isLeft || bundle.items.map(_.evidenceId).distinct.size !=
        bundle.items.size
    ) return Rejected("invalid-evidence-bundle")
    // Resolve existing indexes before any write, including their content binding.
    bundle.items.foreach { item =>
      getItem(item.evidenceId) match {
        case Missing                                              => ()
        case result if StorageResult.value(result).contains(item) => ()
        case result if StorageResult.successful(result) =>
          return Rejected("evidence-item-id-conflict")
        case Rejected(code) => return Rejected(code)
        case _              => return Rejected("evidence-item-index-unavailable")
      }
    }
    val saved = bundles.put(bundle)
    if (!StorageResult.successful(saved)) return saved
    bundle.items.foreach { item =>
      pointer(item.evidenceId) match {
        case Missing =>
          val p = EvidenceItemPointer(item.evidenceId, bundle.bundleId, hash(item))
          val bytes = CoreJson.compact(p).getBytes(UTF_8).toVector
          if (bytes.size > maxPointerBytes) return Rejected("evidence-item-pointer-bound")
          val write = objects.put(key(item.evidenceId), bytes, "application/json", Map.empty)
          if (!StorageResult.successful(write)) {
            // Another writer may have indexed the same immutable item concurrently.
            if (!StorageResult.value(getItem(item.evidenceId)).contains(item))
              return Rejected("evidence-item-index-write-failed")
          }
        case r if StorageResult.value(r).exists(_.itemSha256 == hash(item)) => ()
        case _ => return Rejected("evidence-item-id-conflict")
      }
    }
    saved
  }
}

package edu.uic.cs441.scholarchain.storage.fakes

import edu.uic.cs441.scholarchain.core.RuntimeAuditEnvelope
import edu.uic.cs441.scholarchain.storage.*

/** Uses the same publication and integrity boundary as production, with offline storage ports. */
final class InMemoryRuntimeAuditStore(
    config: RuntimeAuditStoreConfig = RuntimeAuditStoreConfig("fake-runtime-audits")
) extends RuntimeAuditStore {
  private val delegate = new ObjectStoreRuntimeAuditStore(
    new InMemoryObjectStore(config.maxAuditBytes),
    new InMemoryQuerySessionStore,
    config
  )
  def put(envelope: RuntimeAuditEnvelope): StorageResult[RuntimeAuditEnvelope] =
    delegate.put(envelope)
  def get(queryId: String): StorageResult[RuntimeAuditEnvelope] = delegate.get(queryId)
}

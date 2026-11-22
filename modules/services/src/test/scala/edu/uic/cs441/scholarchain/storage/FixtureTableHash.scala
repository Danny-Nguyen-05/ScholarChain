package edu.uic.cs441.scholarchain.storage

/** Test-only access to the producer's logical table hash. The function is package-private to the
  * storage package; this file lives in the same package name (in the services test tree) so the
  * services fixtures use the loader's own hash instead of a second copy of the algorithm.
  */
object FixtureTableHash {
  def of(rows: Vector[ujson.Value]): String = Phase6RuntimeArtifacts.tableHash(rows)
}

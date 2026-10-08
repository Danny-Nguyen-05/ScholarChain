package edu.uic.cs441.scholarchain.core

/** Wire schema versions. Unsupported versions are rejected by validation and config loading.
  *
  * Hadoop preparation limits use [[hadoopPrep]]. That version is not a domain-record version and
  * not a [[config]] version, so existing `scholarchain.config.v1` profiles stay loadable.
  */
object SchemaVersions {
  val domain: String = "scholarchain.domain.v1"
  val config: String = "scholarchain.config.v1"
  val hadoopPrep: String = "scholarchain.hadoop-prep.v1"

  val supportedDomain: Set[String] = Set(domain)
  val supportedConfig: Set[String] = Set(config)
  val supportedHadoopPrep: Set[String] = Set(hadoopPrep)

  /** Versions a [[RunManifest]] may store in `configSchemaVersion`. Application loading stays on
    * [[supportedConfig]] only.
    */
  val supportedManifestConfig: Set[String] = supportedConfig ++ supportedHadoopPrep
}

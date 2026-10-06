package edu.uic.cs441.scholarchain.core

/** Wire schema versions. Unsupported versions are rejected by validation and config loading. */
object SchemaVersions {
  val domain: String = "scholarchain.domain.v1"
  val config: String = "scholarchain.config.v1"

  val supportedDomain: Set[String] = Set(domain)
  val supportedConfig: Set[String] = Set(config)
}

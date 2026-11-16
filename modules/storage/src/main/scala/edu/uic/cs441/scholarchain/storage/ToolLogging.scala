package edu.uic.cs441.scholarchain.storage

/** Logging for the storage command-line tools. Logback with no configuration logs everything at
  * DEBUG, which prints AWS SDK signer and HTTP wire lines carrying temporary session tokens. The
  * tools therefore select the packaged [[resource]] (root INFO; AWS SDK, Apache HTTP and Netty at
  * WARN) through `logback.configurationFile`, which logback accepts as a class-path resource name.
  *
  * Call [[install]] first in `main`, before any logger exists. An operator who already set
  * `logback.configurationFile` (for example the sbt `SBT_OPTS` file) keeps that choice.
  */
object ToolLogging {
  val property: String = "logback.configurationFile"
  val resource: String = "scholarchain/tools-logback.xml"

  /** Returns the configuration logback will read: the operator's value or [[resource]]. */
  def install(): String = synchronized {
    Option(System.getProperty(property)).map(_.trim).filter(_.nonEmpty) match {
      case Some(operator) => operator
      case None           => System.setProperty(property, resource); resource
    }
  }
}

package scholarchain.build

object Java17Guard {
  def requireJava17(specificationVersion: String): Unit =
    require(
      specificationVersion == "17",
      s"ScholarChain check requires Java 17; found Java $specificationVersion. Set JAVA_HOME to JDK 17 and put its bin directory first on PATH."
    )
}

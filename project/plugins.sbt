val ledgerSbtScalafmtVersion = {
  val candidates = Seq(file("Versions.scala"), file("project/Versions.scala"))
  val ledger = candidates.find(_.exists()).getOrElse {
    sys.error(
      s"Could not locate Versions.scala ledger (tried ${candidates.map(_.getAbsolutePath).mkString(", ")})"
    )
  }
  val pattern = """val\s+sbtScalafmt\s*=\s*"([^"]+)"""".r
  scala.io.Source
    .fromFile(ledger)
    .getLines()
    .flatMap(line => pattern.findFirstMatchIn(line).map(_.group(1)))
    .toList
    .headOption
    .getOrElse(sys.error(s"Could not read sbtScalafmt from ${ledger.getAbsolutePath}"))
}

addSbtPlugin("org.scalameta" % "sbt-scalafmt" % ledgerSbtScalafmtVersion)

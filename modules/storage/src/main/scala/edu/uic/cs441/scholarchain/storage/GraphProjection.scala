package edu.uic.cs441.scholarchain.storage

/** The one definition of the Neptune openCypher edge projection. `NeptuneExportValidator` compares
  * the sidecar CSV with `graphEdge` and `coauthorFromRow`; the local loader derives its edge
  * property maps from the same columns, so the local graph carries exactly what the CSV loader
  * would store. A column is `header -> cell`: JSON cells are the exact `render()` of the Parquet
  * struct, integers are numbers, and an absent value is `ujson.Null`.
  */
private[storage] object GraphProjection {
  type Columns = Vector[(String, ujson.Value)]

  /** Evidence table named by every coauthor edge row. */
  val coauthorEvidenceTable = "edges/type=coauthored_with_support"

  private def cell(row: ujson.Obj, name: String): ujson.Value = row.obj.getOrElse(name, ujson.Null)
  private def json(v: ujson.Value): ujson.Value =
    if (v == ujson.Null) ujson.Null else ujson.Str(v.render())

  def graphEdge(row: ujson.Obj): Columns = Vector(
    ":ID" -> cell(row, "edgeId"),
    ":START_ID" -> cell(row, "fromId"),
    ":END_ID" -> cell(row, "toId"),
    ":TYPE" -> cell(row, "edgeType"),
    "schemaVersion:String" -> cell(row, "schemaVersion"),
    "policyVersion:String" -> cell(row, "policyVersion"),
    "sourceEvidenceJson:String" -> json(cell(row, "sourceEvidence")),
    "propertiesJson:String" -> json(cell(row, "properties")),
    "provenanceJson:String" -> json(cell(row, "provenance")),
    "contextJson:String" -> json(cell(row, "context"))
  )

  private def int(v: Option[Int]): ujson.Value =
    v.map(n => ujson.Num(n.toDouble)).getOrElse(ujson.Null)

  /** Coauthor columns from already extracted values; JSON cells are given as rendered text. */
  def coauthor(
      edgeId: String,
      from: String,
      to: String,
      policyVersion: String,
      jointPublicationCount: Long,
      firstYear: Option[Int],
      lastYear: Option[Int],
      windowStartYear: Option[Int],
      windowEndYear: Option[Int],
      windowId: Option[String],
      representativeWorkIdsJson: Option[String],
      contextJson: Option[String]
  ): Columns = Vector(
    ":ID" -> ujson.Str(edgeId),
    ":START_ID" -> ujson.Str(from),
    ":END_ID" -> ujson.Str(to),
    ":TYPE" -> ujson.Str("COAUTHORED_WITH"),
    "policyVersion:String" -> ujson.Str(policyVersion),
    "jointPublicationCount:Long" -> ujson.Num(jointPublicationCount.toDouble),
    "firstCollaborationYear:Int" -> int(firstYear),
    "lastCollaborationYear:Int" -> int(lastYear),
    "windowStartYear:Int" -> int(windowStartYear),
    "windowEndYear:Int" -> int(windowEndYear),
    "windowId:String" -> windowId.map(ujson.Str(_)).getOrElse(ujson.Null),
    "representativeWorkIdsJson:String" ->
      representativeWorkIdsJson.map(ujson.Str(_)).getOrElse(ujson.Null),
    "evidenceTable:String" -> ujson.Str(coauthorEvidenceTable),
    "evidenceEdgeId:String" -> ujson.Str(edgeId),
    "contextJson:String" -> contextJson.map(ujson.Str(_)).getOrElse(ujson.Null)
  )

  /** The validator's path: values read from the exported Parquet row. */
  def coauthorFromRow(row: ujson.Obj): Columns = {
    def optInt(name: String): Option[Int] = cell(row, name) match {
      case ujson.Null => None
      case v          => Some(v.num.toInt)
    }
    def rendered(v: ujson.Value): Option[String] = if (v == ujson.Null) None else Some(v.render())
    val context = cell(row, "context")
    coauthor(
      cell(row, "edgeId").str,
      cell(row, "researcherA").str,
      cell(row, "researcherB").str,
      cell(row, "policyVersion").str,
      cell(row, "jointPublicationCount").num.toLong,
      optInt("firstCollaborationYear"),
      optInt("lastCollaborationYear"),
      optInt("windowStartYear"),
      optInt("windowEndYear"),
      context match {
        case o: ujson.Obj => o.obj.get("windowId").flatMap(_.strOpt)
        case _            => None
      },
      rendered(cell(row, "representativeWorkIds")),
      rendered(context)
    )
  }

  def toObj(columns: Columns): ujson.Obj = ujson.Obj.from(columns)

  /** Edge properties as the graph reader returns them: the structural columns (`:ID`, `:START_ID`,
    * `:END_ID`, `:TYPE`) are dropped, the `:Type` suffix is stripped from each header, null cells
    * are absent and numbers are exact decimal text.
    */
  def properties(columns: Columns): Map[String, String] = columns.iterator
    .filterNot((header, _) => header.startsWith(":"))
    .flatMap { (header, value) =>
      val name = header.takeWhile(_ != ':')
      value match {
        case ujson.Null   => None
        case ujson.Str(s) => Some(name -> s)
        case ujson.Num(n) => Some(name -> BigDecimal(n).toBigInt.toString)
        case other        => Some(name -> other.render())
      }
    }
    .toMap
}

package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.spark.Phase6CInput
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.types.*
import scala.jdk.CollectionConverters.*

/** Synthetic test-only adapter for independently authored source records. */
private[independent] object IndependentPhase6FGFixtures {
  import IndependentPhase6G1.*
  private val string = StringType
  private val integer = IntegerType
  private val stringArray = ArrayType(StringType, containsNull = false)

  private def frame(
      spark: SparkSession,
      columns: Seq[(String, DataType)],
      records: Seq[Seq[Any]]
  ): DataFrame = {
    val schema = StructType(columns.map { case (name, dataType) =>
      StructField(name, dataType, nullable = true)
    })
    spark.createDataFrame(records.map(Row.fromSeq).asJava, schema)
  }

  def input(spark: SparkSession, works: Vector[WorkRecord] = allWorks): Phase6CInput = {
    val dblpW1 = dblpWorks.head
    val crossref = works.find(_.source == SourceType.Crossref)
    val workLinks = crossref.toVector.map(w => Seq(dblpW1.workId, w.workId))
    val researcherLinks = crossref.toVector.flatMap(w =>
      dblpW1.authors.zip(w.authors).map((a, b) => Seq(a.mentionId, b.mentionId))
    )
    val inputTeams = works.map(w =>
      Seq(w.workId, w.source.wire, w.sourceRecordId, w.authors.map(_.mentionId).asJava)
    )
    val inputPairs = works.flatMap { w =>
      for {
        left <- w.authors.indices
        right <- (left + 1) until w.authors.size
      } yield Seq(
        w.workId,
        w.source.wire,
        w.sourceRecordId,
        w.authors(left).mentionId,
        w.authors(right).mentionId,
        w.year.map(Int.box).orNull
      )
    }
    Phase6CInput(
      works = frame(
        spark,
        Seq(
          "workId" -> string,
          "source" -> string,
          "sourceRecordId" -> string,
          "year" -> integer,
          "title" -> string,
          "doi" -> string,
          "arxivId" -> string,
          "venueId" -> string,
          "snapshot" -> string
        ),
        works.map(w =>
          Seq(
            w.workId,
            w.source.wire,
            w.sourceRecordId,
            w.year.map(Int.box).orNull,
            w.title,
            w.doi.orNull,
            w.arxivId.orNull,
            w.venueId.orNull,
            w.provenance.datasetSnapshot
          )
        )
      ),
      mentions = frame(
        spark,
        Seq(
          "mentionId" -> string,
          "source" -> string,
          "sourceRecordId" -> string,
          "nameText" -> string,
          "observedOrcid" -> string,
          "snapshot" -> string
        ),
        works.flatMap(w =>
          w.authors.map(m =>
            Seq(
              m.mentionId,
              m.source.wire,
              m.sourceRecordId,
              m.nameText,
              m.observedOrcid.orNull,
              m.provenance.datasetSnapshot
            )
          )
        )
      ),
      teams = frame(
        spark,
        Seq(
          "workId" -> string,
          "source" -> string,
          "sourceRecordId" -> string,
          "memberMentionIds" -> stringArray
        ),
        inputTeams
      ),
      pairs = frame(
        spark,
        Seq(
          "workId" -> string,
          "source" -> string,
          "sourceRecordId" -> string,
          "leftMentionId" -> string,
          "rightMentionId" -> string,
          "year" -> integer
        ),
        inputPairs
      ),
      researcherLinks = frame(spark, Seq("leftId" -> string, "rightId" -> string), researcherLinks),
      workLinks = frame(spark, Seq("leftId" -> string, "rightId" -> string), workLinks),
      researcherCannotLinks = frame(spark, Seq("leftId" -> string, "rightId" -> string), Seq.empty),
      workCannotLinks = frame(spark, Seq("leftId" -> string, "rightId" -> string), Seq.empty),
      researcherAuthority = frame(
        spark,
        Seq("endpointId" -> string, "namespace" -> string, "value" -> string),
        Seq.empty
      ),
      workAuthority = frame(
        spark,
        Seq("endpointId" -> string, "namespace" -> string, "value" -> string),
        Seq.empty
      )
    )
  }

}

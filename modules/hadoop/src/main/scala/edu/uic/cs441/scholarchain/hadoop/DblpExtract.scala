package edu.uic.cs441.scholarchain.hadoop

import edu.uic.cs441.scholarchain.core.*

import scala.collection.mutable.ArrayBuffer

/** Streaming DBLP XML. Gzip is not splittable; uncompressed files split on record boundaries. The
  * committed sample is uncompressed and its DOCTYPE is an empty internal subset. An approved local
  * SYSTEM id uses the classpath catalogue and is not opened as a file or URL.
  */
object DblpXml {
  val RecordNames: Set[String] = Set(
    "article",
    "inproceedings",
    "proceedings",
    "book",
    "incollection",
    "phdthesis",
    "mastersthesis",
    "www",
    "data",
    "person"
  )
  val Supported: Set[String] = RecordNames -- Set("www", "data", "person")

  final case class Header(entities: Map[String, String], unsafe: Option[String])

  private val DatedDtd = "dblp-\\d{4}-\\d{2}-\\d{2}\\.dtd"
  private val SystemDoctype =
    "(?i)<!DOCTYPE\\s+[A-Za-z0-9:_-]+\\s+SYSTEM\\s+(\"[^\"]*\"|'[^']*'|[^\\s\\[>]+)".r
  private val ExternalDoctype = "(?i)<!DOCTYPE\\s+[A-Za-z0-9:_-]+\\s+SYSTEM\\b".r

  /** Approved basenames are `dblp.dtd` and `dblp-YYYY-MM-DD.dtd`. The literal is rejected when it
    * contains `:`, `//`, a backslash, or `..`. The path is never read.
    */
  def approvedSystemLiteral(token: String): Boolean = {
    val value = unquoteSystem(token).trim
    if (
      value.isEmpty || value.contains(':') || value.contains("//") || value.contains('\\') ||
      value.contains("..")
    ) false
    else {
      val slash = value.lastIndexOf('/')
      val segment = if (slash >= 0) value.substring(slash + 1) else value
      segment == "dblp.dtd" || segment.matches(DatedDtd)
    }
  }

  def header(prefix: String): Header = {
    val externalEntity = "(?i)<!ENTITY\\b[^>]*\\bSYSTEM\\b".r
    val publicEntity = "(?i)<!ENTITY\\b[^>]*\\bPUBLIC\\b".r
    val literals = SystemDoctype.findAllMatchIn(prefix).map(_.group(1)).toVector
    val sawSystem = ExternalDoctype.findFirstIn(prefix).nonEmpty
    val unapproved = literals.exists(token => !approvedSystemLiteral(token))
    val unsafe =
      if (unapproved || (sawSystem && literals.isEmpty)) Some("external DTD")
      else if (externalEntity.findFirstIn(prefix).nonEmpty) Some("external entity")
      else if (publicEntity.findFirstIn(prefix).nonEmpty) Some("public external entity")
      else None
    val internal = internalEntities(prefix)
    val approved = unsafe.isEmpty && literals.exists(approvedSystemLiteral)
    val entities = if (approved) namedEntityCatalogue ++ internal else internal
    Header(entities, unsafe)
  }

  /** Decoded catalogue characters. Loaded once from `dblp-named-entities.v1.tsv`. */
  private[hadoop] def namedEntityCatalogue: Map[String, String] = NamedEntityCatalogue.values

  private def unquoteSystem(token: String): String = {
    val trimmed = token.trim
    if (
      trimmed.length >= 2 &&
      ((trimmed.charAt(0) == '"' && trimmed.charAt(trimmed.length - 1) == '"') ||
        (trimmed.charAt(0) == '\'' && trimmed.charAt(trimmed.length - 1) == '\''))
    ) trimmed.substring(1, trimmed.length - 1)
    else trimmed
  }

  private object NamedEntityCatalogue {
    lazy val values: Map[String, String] = {
      val resource = "/dblp-named-entities.v1.tsv"
      val in = Option(DblpXml.getClass.getResourceAsStream(resource)).getOrElse(
        throw new IllegalStateException(s"classpath resource $resource is missing")
      )
      try {
        val text = new String(in.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8)
        text
          .split("\n", -1)
          .iterator
          .map(_.stripSuffix("\r"))
          .filter(line => line.nonEmpty && !line.startsWith("#"))
          .map { line =>
            val tab = line.indexOf('\t')
            if (tab <= 0 || tab == line.length - 1)
              throw new IllegalStateException(s"malformed catalogue line: $line")
            val name = line.substring(0, tab)
            if (Set("amp", "lt", "gt", "quot", "apos").contains(name))
              throw new IllegalStateException(s"predefined entity in catalogue: $name")
            name -> decodeCharRef(line.substring(tab + 1).trim)
          }
          .toMap
      } finally in.close()
    }

    private def decodeCharRef(raw: String): String = {
      if (!raw.startsWith("&#") || !raw.endsWith(";"))
        throw new IllegalStateException(s"catalogue replacement is not a character reference: $raw")
      val body = raw.substring(2, raw.length - 1)
      val cp =
        if (body.startsWith("x") || body.startsWith("X")) Integer.parseInt(body.substring(1), 16)
        else Integer.parseInt(body, 10)
      new String(Character.toChars(cp))
    }
  }

  def internalEntities(prefix: String): Map[String, String] = {
    val pattern =
      "(?i)<!ENTITY\\s+([A-Za-z][A-Za-z0-9._-]*)\\s+(?:\"([^\"]*)\"|'([^']*)')\\s*>".r
    pattern
      .findAllMatchIn(prefix)
      .map(m => m.group(1) -> Option(m.group(2)).getOrElse(m.group(3)))
      .toMap
  }

  /** One left-to-right expansion. Predefined entities and character references become character
    * data and are not scanned again, so `&amp;` and `&#38;` stay an ampersand. Named entities
    * expand recursively, which is what keeps a billion-laughs payload over the size limit. The
    * result is not reparsed as markup.
    */
  def expand(
      xml: String,
      entities: Map[String, String],
      max: Long
  ): Either[RejectReasonCode, String] =
    expandAt(xml, entities, max, depth = 0)

  private def expandAt(
      xml: String,
      entities: Map[String, String],
      max: Long,
      depth: Int
  ): Either[RejectReasonCode, String] = {
    if (depth > 16) return Left(RejectReasonCode.OversizeXmlEntityExpansion)
    val next = new StringBuilder
    var size = 0L
    var i = 0
    while (i < xml.length) {
      if (xml.charAt(i) != '&') {
        next.append(xml.charAt(i))
        size += 1
        if (size > max) return Left(RejectReasonCode.OversizeXmlEntityExpansion)
        i += 1
      } else {
        val semi = xml.indexOf(';', i)
        if (semi < 0) return Left(RejectReasonCode.MalformedRecord)
        val token = xml.substring(i + 1, semi)
        resolve(token, entities) match {
          case Left(code) => return Left(code)
          case Right(Literal(text)) =>
            size += text.length.toLong
            if (size > max) return Left(RejectReasonCode.OversizeXmlEntityExpansion)
            next.append(text)
          case Right(Named(body)) =>
            expandAt(body, entities, max - size, depth + 1) match {
              case Left(code) => return Left(code)
              case Right(text) =>
                size += text.length.toLong
                if (size > max) return Left(RejectReasonCode.OversizeXmlEntityExpansion)
                next.append(text)
            }
        }
        i = semi + 1
      }
    }
    Right(next.toString)
  }

  private sealed trait Replacement
  private final case class Literal(text: String) extends Replacement
  private final case class Named(body: String) extends Replacement

  private def resolve(
      token: String,
      entities: Map[String, String]
  ): Either[RejectReasonCode, Replacement] =
    token match {
      case "lt"   => Right(Literal("<"))
      case "gt"   => Right(Literal(">"))
      case "amp"  => Right(Literal("&"))
      case "quot" => Right(Literal("\""))
      case "apos" => Right(Literal("'"))
      case decimal if decimal.startsWith("#x") || decimal.startsWith("#X") =>
        parseCodePoint(decimal.drop(2), 16).map(Literal.apply)
      case decimal if decimal.startsWith("#") =>
        parseCodePoint(decimal.drop(1), 10).map(Literal.apply)
      case name if entities.contains(name) =>
        val body = entities(name)
        if (body.indexOf('&') >= 0) Right(Named(body)) else Right(Literal(body))
      case name if name.contains("://") || name.startsWith("#") =>
        Left(RejectReasonCode.UnsafeEntity)
      case _ => Left(RejectReasonCode.MalformedRecord)
    }

  private def parseCodePoint(digits: String, radix: Int): Either[RejectReasonCode, String] =
    try {
      val cp = Integer.parseInt(digits, radix)
      if (cp < 0 || cp > 0x10ffff) Left(RejectReasonCode.MalformedRecord)
      else Right(new String(Character.toChars(cp)))
    } catch {
      case _: NumberFormatException => Left(RejectReasonCode.MalformedRecord)
    }

  def children(xml: String, name: String): Vector[String] =
    childrenMarkup(xml, name).map(characterData)

  /** Inner markup with CDATA boundaries retained until entity expansion. */
  def childrenMarkup(xml: String, name: String): Vector[String] = {
    val found = ArrayBuffer.empty[String]
    var i = 0
    while (i < xml.length) {
      val open = indexOfTag(xml, name, i, end = false)
      if (open < 0) i = xml.length
      else {
        val closeStart = tagEnd(xml, open)
        if (closeStart < 0) i = xml.length
        else if (closeStart > 0 && xml.charAt(closeStart - 1) == '/') {
          found += ""
          i = closeStart + 1
        } else {
          val innerStart = closeStart + 1
          val end = matchingEnd(xml, name, innerStart)
          if (end < 0) i = xml.length
          else {
            found += xml.substring(innerStart, end)
            val after = tagEnd(xml, end)
            i = if (after < 0) xml.length else after + 1
          }
        }
      }
    }
    found.toVector
  }

  def rootName(xml: String): Option[String] = {
    val start = xml.indexOf('<')
    if (start < 0 || start + 1 >= xml.length) None
    else if (xml.charAt(start + 1) == '/' || xml.charAt(start + 1) == '!') None
    else {
      val name = readXmlName(xml, start + 1)
      if (name.isEmpty) None else Some(name)
    }
  }

  def attr(xml: String, name: String): Option[String] = {
    var i = 0
    while (i < xml.length) {
      if (xml.charAt(i) != '<') i += 1
      else if (specialAt(xml, i)) i = skipSpecial(xml, i)
      else if (i + 1 < xml.length && xml.charAt(i + 1) == '/') {
        val gt = tagEnd(xml, i)
        i = if (gt < 0) xml.length else gt + 1
      } else if (i + 1 < xml.length && isXmlNameStart(xml.charAt(i + 1))) {
        val gt = tagEnd(xml, i)
        if (gt < 0) return None
        attributeValue(xml, i, gt, name) match {
          case some @ Some(_) => return some
          case None           => i = gt + 1
        }
      } else i += 1
    }
    None
  }

  /** Outer markup of each element. Comments, CDATA, and processing instructions are not elements. A
    * self-closing tag is the same element as an empty pair.
    */
  def elements(xml: String, name: String): Vector[String] = {
    val found = ArrayBuffer.empty[String]
    var i = 0
    while (i < xml.length) {
      val open = indexOfTag(xml, name, i, end = false)
      if (open < 0) i = xml.length
      else {
        val gt = tagEnd(xml, open)
        if (gt < 0) i = xml.length
        else if (gt > open && xml.charAt(gt - 1) == '/') {
          found += xml.substring(open, gt + 1)
          i = gt + 1
        } else {
          val end = matchingEnd(xml, name, gt + 1)
          if (end < 0) i = xml.length
          else {
            val after = tagEnd(xml, end)
            if (after < 0) i = xml.length
            else {
              found += xml.substring(open, after + 1)
              i = after + 1
            }
          }
        }
      }
    }
    found.toVector
  }

  /** Character data of `xml`. CDATA sections contribute their text. Comments and processing
    * instructions contribute nothing. Other markup is copied through.
    */
  def characterData(xml: String): String = {
    if (xml.indexOf("<!") < 0 && xml.indexOf("<?") < 0) xml
    else {
      val out = new StringBuilder(xml.length)
      var i = 0
      while (i < xml.length) {
        if (xml.charAt(i) != '<') {
          out.append(xml.charAt(i))
          i += 1
        } else if (specialAt(xml, i)) {
          if (xml.startsWith("<![CDATA[", i)) {
            val content = i + 9
            val end = xml.indexOf("]]>", content)
            if (end < 0) {
              out.append(xml.substring(content))
              i = xml.length
            } else {
              out.append(xml.substring(content, end))
              i = end + 3
            }
          } else i = skipSpecial(xml, i)
        } else {
          out.append('<')
          i += 1
        }
      }
      out.toString
    }
  }

  /** XML references are active in ordinary text only. CDATA is literal; all segments share the same
    * expansion budget. Comments and processing instructions contribute no characters.
    */
  def expandCharacterData(
      xml: String,
      entities: Map[String, String],
      max: Long
  ): Either[RejectReasonCode, String] = {
    val out = new StringBuilder
    var i = 0
    while (i < xml.length) {
      if (xml.startsWith("<![CDATA[", i)) {
        val end = xml.indexOf("]]>", i + 9)
        if (end < 0) return Left(RejectReasonCode.MalformedRecord)
        val length = end - i - 9
        if (length.toLong > max - out.length)
          return Left(RejectReasonCode.OversizeXmlEntityExpansion)
        out.append(xml.substring(i + 9, end))
        i = end + 3
      } else if (xml.charAt(i) == '<' && specialAt(xml, i)) i = skipSpecial(xml, i)
      else {
        val start = i
        i += 1
        while (i < xml.length && !(xml.charAt(i) == '<' && specialAt(xml, i))) i += 1
        expand(xml.substring(start, i), entities, max - out.length) match {
          case Left(code)  => return Left(code)
          case Right(text) => out.append(text)
        }
      }
    }
    Right(out.toString)
  }

  private def indexOfTag(xml: String, name: String, from: Int, end: Boolean): Int = {
    val needle = if (end) "</" + name else "<" + name
    var i = from
    while (i < xml.length) {
      if (xml.charAt(i) != '<') i += 1
      else if (specialAt(xml, i)) i = skipSpecial(xml, i)
      else if (xml.startsWith(needle, i)) {
        val after = i + needle.length
        if (after >= xml.length || isBoundary(xml.charAt(after))) return i
        i = after
      } else i += 1
    }
    -1
  }

  private def specialAt(xml: String, i: Int): Boolean =
    i + 1 < xml.length && (xml.charAt(i + 1) == '!' || xml.charAt(i + 1) == '?')

  private def skipSpecial(xml: String, from: Int): Int = {
    val next =
      if (xml.startsWith("<!--", from)) {
        val end = xml.indexOf("-->", from + 4)
        if (end < 0) xml.length else end + 3
      } else if (xml.startsWith("<![CDATA[", from)) {
        val end = xml.indexOf("]]>", from + 9)
        if (end < 0) xml.length else end + 3
      } else if (from + 1 < xml.length && xml.charAt(from + 1) == '?') {
        val end = xml.indexOf("?>", from + 2)
        if (end < 0) xml.length else end + 2
      } else {
        var i = math.min(from + 2, xml.length)
        var quote = 0
        var bracket = 0
        var stop = xml.length
        var done = false
        while (i < xml.length && !done) {
          val ch = xml.charAt(i)
          if (quote != 0) {
            if (ch == quote) quote = 0
          } else if (ch == '"' || ch == '\'') quote = ch
          else if (ch == '[') bracket += 1
          else if (ch == ']' && bracket > 0) bracket -= 1
          else if (ch == '>' && bracket == 0) {
            stop = i + 1
            done = true
          }
          if (!done) i += 1
        }
        stop
      }
    if (next <= from) from + 1 else next
  }

  private def tagEnd(xml: String, open: Int): Int = {
    var i = open
    var quote = 0
    while (i < xml.length) {
      val ch = xml.charAt(i)
      if (quote != 0) {
        if (ch == quote) quote = 0
      } else if (ch == '"' || ch == '\'') quote = ch
      else if (ch == '>') return i
      i += 1
    }
    -1
  }

  private def attributeValue(xml: String, open: Int, gt: Int, name: String): Option[String] = {
    var i = open + 1
    while (i <= gt && i < xml.length && isXmlNameChar(xml.charAt(i))) i += 1
    while (i < gt) {
      val ch = xml.charAt(i)
      if (ch == '"' || ch == '\'') {
        val quote = ch
        i += 1
        while (i < gt && xml.charAt(i) != quote) i += 1
        if (i < gt) i += 1
      } else if (isXmlNameStart(ch)) {
        val start = i
        i += 1
        while (i < gt && isXmlNameChar(xml.charAt(i))) i += 1
        val token = xml.substring(start, i)
        while (i < gt && xml.charAt(i).isWhitespace) i += 1
        if (token.equalsIgnoreCase(name) && i < gt && xml.charAt(i) == '=') {
          i += 1
          while (i < gt && xml.charAt(i).isWhitespace) i += 1
          if (i < gt && (xml.charAt(i) == '"' || xml.charAt(i) == '\'')) {
            val quote = xml.charAt(i)
            val valueStart = i + 1
            val valueEnd = xml.indexOf(quote, valueStart)
            if (valueEnd >= 0 && valueEnd <= gt) return Some(xml.substring(valueStart, valueEnd))
          }
        }
      } else i += 1
    }
    None
  }

  private def isXmlNameStart(ch: Char): Boolean =
    ch.isLetter || ch == '_' || ch == ':'

  private def isXmlNameChar(ch: Char): Boolean =
    isXmlNameStart(ch) || ch.isDigit || ch == '-' || ch == '.'

  private def matchingEnd(xml: String, name: String, from: Int): Int = {
    var depth = 1
    var i = from
    while (i < xml.length && depth > 0) {
      val nextOpen = indexOfTag(xml, name, i, end = false)
      val nextEnd = indexOfTag(xml, name, i, end = true)
      if (nextEnd < 0) return -1
      if (nextOpen >= 0 && nextOpen < nextEnd) {
        depth += 1
        i = nextOpen + name.length + 1
      } else {
        depth -= 1
        if (depth == 0) return nextEnd
        i = nextEnd + name.length + 2
      }
    }
    -1
  }

  private def isBoundary(ch: Char): Boolean =
    ch.isWhitespace || ch == '>' || ch == '/'

  private def readXmlName(xml: String, from: Int): String = {
    val out = new StringBuilder
    var i = from
    while (
      i < xml.length && (xml.charAt(i).isLetterOrDigit || xml
        .charAt(i) == '_' || xml.charAt(i) == '-')
    ) {
      out.append(xml.charAt(i))
      i += 1
    }
    out.toString
  }
}

object DblpRecords {
  def parse(
      rawXml: String,
      header: DblpXml.Header,
      runId: String,
      snapshot: String,
      locator: String,
      maxRecordBytes: Long,
      maxExpansion: Long,
      retrievalDate: Option[String] = None
  ): Vector[EmittedRecord] = {
    val sourceBytes = Digests.bytesOf(rawXml)
    if (header.unsafe.nonEmpty)
      Vector(
        reject(
          Some(SourceType.Dblp),
          locator,
          snapshot,
          runId,
          RejectReasonCode.UnsafeEntity,
          header.unsafe.get
        )
      )
    else if (sourceBytes > maxRecordBytes)
      Vector(
        reject(
          Some(SourceType.Dblp),
          locator,
          snapshot,
          runId,
          RejectReasonCode.OversizeRecord,
          rawXml.take(200)
        )
      )
    else {
      val stream = new PosStream(
        new java.io.ByteArrayInputStream(rawXml.getBytes(java.nio.charset.StandardCharsets.UTF_8))
      )
      val framed = DblpSplitReader.nextOpen(stream, Long.MaxValue).map { open =>
        open -> DblpSplitReader.readElement(stream, open, maxRecordBytes)
      }
      var trailingWhitespace = true
      var tail = stream.read()
      while (tail >= 0) {
        if (tail != ' ' && tail != '\t' && tail != '\r' && tail != '\n') trailingWhitespace = false
        tail = stream.read()
      }
      val badFrame = framed.forall { case (open, record) =>
        !rawXml.take(open.at.toInt).forall(_.isWhitespace) || record.unterminated ||
        record.malformed || !trailingWhitespace || stream.pos != sourceBytes
      }
      if (badFrame)
        Vector(
          reject(
            Some(SourceType.Dblp),
            locator,
            snapshot,
            runId,
            RejectReasonCode.MalformedRecord,
            rawXml.take(180)
          )
        )
      else if (framed.exists(_._2.oversize))
        Vector(
          reject(
            Some(SourceType.Dblp),
            locator,
            snapshot,
            runId,
            RejectReasonCode.OversizeRecord,
            rawXml.take(180)
          )
        )
      else build(rawXml, header.entities, maxExpansion, runId, snapshot, locator, retrievalDate)
    }
  }

  private def build(
      xml: String,
      entities: Map[String, String],
      maxExpansion: Long,
      runId: String,
      snapshot: String,
      locator: String,
      retrievalDate: Option[String]
  ): Vector[EmittedRecord] = {
    val name = DblpXml.rootName(xml).getOrElse("")
    val key = DblpXml
      .attr(xml.take(xml.indexOf('>').max(0) + 1), "key")
      .flatMap(value => DblpXml.expand(value, entities, maxExpansion).toOption)
    val located = key.map(value => locator + "#" + value).getOrElse(locator)
    if (!DblpXml.RecordNames.contains(name))
      Vector(
        reject(
          None,
          located,
          Some(snapshot),
          runId,
          RejectReasonCode.MalformedRecord,
          xml.take(180)
        )
      )
    else if (!DblpXml.Supported.contains(name))
      Vector(
        reject(
          Some(SourceType.Dblp),
          located,
          Some(snapshot),
          runId,
          RejectReasonCode.UnsupportedRecordType,
          name
        )
      )
    else if (key.forall(_.trim.isEmpty))
      Vector(
        reject(
          Some(SourceType.Dblp),
          located,
          Some(snapshot),
          runId,
          RejectReasonCode.MissingRequiredField,
          "missing key"
        )
      )
    else {
      val recordKey = key.get.trim
      val titles = DblpXml.childrenMarkup(xml, "title").flatMap { inner =>
        DblpXml.expandCharacterData(inner, entities, maxExpansion) match {
          case Right(text) => Some(text)
          case Left(_)     => None
        }
      }
      val titleFailed = DblpXml.childrenMarkup(xml, "title").exists { inner =>
        DblpXml.expandCharacterData(inner, entities, maxExpansion).isLeft
      }
      if (titleFailed)
        return Vector(
          DblpXml
            .childrenMarkup(xml, "title")
            .flatMap { inner =>
              DblpXml.expandCharacterData(inner, entities, maxExpansion).left.toOption
            }
            .headOption match {
            case Some(code) =>
              reject(Some(SourceType.Dblp), located, Some(snapshot), runId, code, xml.take(180))
            case None =>
              reject(
                Some(SourceType.Dblp),
                located,
                Some(snapshot),
                runId,
                RejectReasonCode.MalformedRecord,
                "title"
              )
          }
        )
      if (titles.isEmpty || titles.head.trim.isEmpty)
        Vector(
          reject(
            Some(SourceType.Dblp),
            located,
            Some(snapshot),
            runId,
            RejectReasonCode.MissingRequiredField,
            "missing title"
          )
        )
      else
        assemble(
          xml,
          entities,
          maxExpansion,
          name,
          recordKey,
          titles.head.trim,
          runId,
          snapshot,
          located,
          retrievalDate
        )
    }
  }

  private def assemble(
      xml: String,
      entities: Map[String, String],
      maxExpansion: Long,
      recordType: String,
      key: String,
      title: String,
      runId: String,
      snapshot: String,
      locator: String,
      retrievalDate: Option[String]
  ): Vector[EmittedRecord] = {
    def texts(name: String): Either[RejectReasonCode, Vector[String]] = {
      val found = DblpXml.childrenMarkup(xml, name)
      val out = ArrayBuffer.empty[String]
      var failure: Option[RejectReasonCode] = None
      found.foreach { inner =>
        if (failure.isEmpty)
          DblpXml.expandCharacterData(inner, entities, maxExpansion) match {
            case Left(code)  => failure = Some(code)
            case Right(text) => out += text
          }
      }
      failure.toLeft(out.toVector)
    }
    val ee = texts("ee") match {
      case Left(code) =>
        return Vector(reject(Some(SourceType.Dblp), locator, Some(snapshot), runId, code, "ee"))
      case Right(values) => values.map(_.trim).filter(_.nonEmpty)
    }
    val doi = ee.iterator.flatMap(normalizeDoiLink).nextOption()
    val badDoi = ee.find(looksLikeDoi).filter(normalizeDoiLink(_).isEmpty)
    if (badDoi.nonEmpty)
      return Vector(
        reject(
          Some(SourceType.Dblp),
          locator,
          Some(snapshot),
          runId,
          RejectReasonCode.InvalidIdentifier,
          badDoi.get
        )
      )
    val yearText = texts("year") match {
      case Left(code) =>
        return Vector(reject(Some(SourceType.Dblp), locator, Some(snapshot), runId, code, "year"))
      case Right(values) => values.headOption.map(_.trim).getOrElse("")
    }
    val year = optionalYear(yearText)
    year match {
      case Left(message) =>
        return Vector(
          reject(
            Some(SourceType.Dblp),
            locator,
            Some(snapshot),
            runId,
            RejectReasonCode.MalformedRecord,
            message
          )
        )
      case Right(_) => ()
    }
    val arxiv = ee.flatMap(value => StableIds.arxivFromSourceUri(Some(value))).headOption
    val workId =
      StableIds.authoritativeWorkIdForRecord(SourceType.Dblp, key, doi, arxiv) match {
        case Right(id) => id
        case Left(error) =>
          return Vector(
            reject(
              Some(SourceType.Dblp),
              locator,
              Some(snapshot),
              runId,
              RejectReasonCode.InvalidIdentifier,
              error.message
            )
          )
      }
    val provenance = ProvenanceFactory(
      SourceType.Dblp,
      key,
      Some(s"https://dblp.org/rec/$key"),
      snapshot,
      runId,
      retrievalDate = retrievalDate
    )
    val mentions = ArrayBuffer.empty[AuthorMention]
    var ordinal = 1
    var authorFailure: Option[EmittedRecord] = None
    val authorXml = authorElements(xml)
    var authorIndex = 0
    while (authorIndex < authorXml.length && authorFailure.isEmpty) {
      val element = authorXml(authorIndex)
      val orcidRaw = DblpXml.attr(element, "orcid").flatMap { raw =>
        DblpXml.expand(raw, entities, maxExpansion) match {
          case Left(code) =>
            authorFailure = Some(
              reject(Some(SourceType.Dblp), locator, Some(snapshot), runId, code, "orcid")
            )
            None
          case Right(text) => Some(text)
        }
      }
      val orcid = orcidRaw.map(normalizeOrcid)
      if (authorFailure.nonEmpty) ()
      else if (orcidRaw.nonEmpty && orcid.forall(_.isLeft))
        authorFailure = Some(
          reject(
            Some(SourceType.Dblp),
            locator,
            Some(snapshot),
            runId,
            RejectReasonCode.InvalidIdentifier,
            orcidRaw.getOrElse("")
          )
        )
      else {
        val name = DblpXml.expandCharacterData(innerText(element), entities, maxExpansion) match {
          case Left(code) =>
            authorFailure = Some(
              reject(Some(SourceType.Dblp), locator, Some(snapshot), runId, code, "author")
            )
            ""
          case Right(text) => text.trim
        }
        if (authorFailure.isEmpty && name.isEmpty)
          authorFailure = Some(
            reject(
              Some(SourceType.Dblp),
              locator,
              Some(snapshot),
              runId,
              RejectReasonCode.MissingRequiredField,
              "blank author"
            )
          )
        else {
          val observed = orcid.flatMap(_.toOption)
          val status =
            if (observed.nonEmpty) MentionIdentityStatus.ExternalIdentifierObserved
            else MentionIdentityStatus.NameOnlyUnconfirmed
          mentions += AuthorMention(
            StableIds.mentionId(SourceType.Dblp, key, ordinal),
            SchemaVersions.domain,
            SourceType.Dblp,
            key,
            ordinal,
            name,
            TextNorm.personName(name),
            observed,
            None,
            status,
            None,
            "DBLP author string is not a resolved researcher",
            provenance
          )
          ordinal += 1
        }
      }
      authorIndex += 1
    }
    if (authorFailure.nonEmpty) return Vector(authorFailure.get)
    val pages = texts("pages") match {
      case Left(code) =>
        return Vector(reject(Some(SourceType.Dblp), locator, Some(snapshot), runId, code, "pages"))
      case Right(values) => values.headOption.map(_.trim).filter(_.nonEmpty)
    }
    val urls = texts("url") match {
      case Left(code) =>
        return Vector(reject(Some(SourceType.Dblp), locator, Some(snapshot), runId, code, "url"))
      case Right(values) => values.map(_.trim).filter(_.nonEmpty)
    }
    val url = urls.headOption
    val external = url.map { value =>
      if (value.startsWith("http://") || value.startsWith("https://")) value
      else s"https://dblp.org/$value"
    }
    val booktitles = texts("booktitle") match {
      case Left(code) =>
        return Vector(
          reject(Some(SourceType.Dblp), locator, Some(snapshot), runId, code, "booktitle")
        )
      case Right(values) => values
    }
    val journals = texts("journal") match {
      case Left(code) =>
        return Vector(
          reject(Some(SourceType.Dblp), locator, Some(snapshot), runId, code, "journal")
        )
      case Right(values) => values
    }
    val venueLabel = booktitles.headOption
      .map(_.trim)
      .filter(_.nonEmpty)
      .orElse(journals.headOption.map(_.trim).filter(_.nonEmpty))
    val venueId = venueLabel.flatMap(label => StableIds.venueIdFromDblpBooktitle(label).toOption)
    val work = WorkRecord(
      SchemaVersions.domain,
      workId,
      SourceType.Dblp,
      key,
      Some(recordType),
      title,
      TextNorm.title(title),
      year.toOption.flatten,
      venueId,
      doi,
      arxiv,
      pages,
      external,
      mentions.toVector,
      None,
      provenance,
      sourceLinks =
        ee.map(value => NamedText("ee", value)) ++ urls.map(value => NamedText("url", value))
    )
    val out = ArrayBuffer.empty[EmittedRecord]
    DomainValidation.check(work) match {
      case Left(errors) =>
        out += reject(
          Some(SourceType.Dblp),
          locator,
          Some(snapshot),
          runId,
          RejectReasonCode.SchemaFailure,
          errors.map(_.message).mkString("; ")
        )
      case Right(valid) =>
        out += EmittedRecord.Work(valid)
        venueLabel.zip(venueId).foreach { case (label, id) =>
          val venue = Venue(
            id,
            SchemaVersions.domain,
            label,
            "dblp-booktitle",
            None,
            "DBLP booktitle or journal label",
            provenance
          )
          DomainValidation.check(venue) match {
            case Left(errors) =>
              out += reject(
                Some(SourceType.Dblp),
                locator,
                Some(snapshot),
                runId,
                RejectReasonCode.SchemaFailure,
                errors.map(_.message).mkString("; ")
              )
            case Right(checked) =>
              out += EmittedRecord.VenueRec(checked)
              val link = EnrichmentLink(
                SchemaVersions.domain,
                SourceType.Dblp,
                key,
                snapshot,
                Some(valid.workId),
                None,
                EnrichmentTargetKind.Venue,
                id,
                None,
                None,
                None,
                "venue label from the DBLP record",
                runId,
                provenance
              )
              DomainValidation.check(link) match {
                case Right(value) => out += EmittedRecord.Link(value)
                case Left(errors) =>
                  out += reject(
                    Some(SourceType.Dblp),
                    locator,
                    Some(snapshot),
                    runId,
                    RejectReasonCode.SchemaFailure,
                    errors.map(_.message).mkString("; ")
                  )
              }
          }
        }
    }
    out.toVector
  }

  private def authorElements(xml: String): Vector[String] =
    DblpXml.elements(xml, "author")

  private def innerText(element: String): String = {
    DblpXml.childrenMarkup(element, "author").headOption.getOrElse("")
  }

  private def looksLikeDoi(value: String): Boolean = {
    val trimmed = value.trim
    trimmed.regionMatches(true, 0, "https://doi.org/", 0, "https://doi.org/".length) ||
    trimmed.regionMatches(true, 0, "http://doi.org/", 0, "http://doi.org/".length) ||
    trimmed.regionMatches(true, 0, "https://dx.doi.org/", 0, "https://dx.doi.org/".length) ||
    trimmed.regionMatches(true, 0, "doi:", 0, 4)
  }

  private def normalizeDoiLink(value: String): Option[String] =
    if (!looksLikeDoi(value)) None else StableIds.normalizeDoi(value).toOption

  private def normalizeOrcid(raw: String): Either[DomainViolation, String] =
    StableIds.researcherIdFromValidatedOrcid(raw).map(_.stripPrefix("researcher:orcid:"))

  private def optionalYear(text: String): Either[String, Option[Int]] =
    if (text.isEmpty) Right(None)
    else
      try {
        val year = text.toInt
        if (year < 1 || year > 9999) Left(text) else Right(Some(year))
      } catch {
        case _: NumberFormatException => Left(text)
      }

  private def reject(
      source: Option[SourceType],
      locator: String,
      snapshot: Option[String] | String,
      runId: String,
      reason: RejectReasonCode,
      raw: String
  ): EmittedRecord = {
    val snap = snapshot match {
      case text: String          => Some(text)
      case other: Option[String] => other
    }
    EmittedRecord.Rejected(
      Rejects.record(source, locator, snap, runId, PreparationStage.Parse, reason, raw)
    )
  }
}

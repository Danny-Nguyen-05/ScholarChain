package edu.uic.cs441.scholarchain.hadoop

import org.apache.hadoop.fs.{Path => HPath}
import org.apache.hadoop.io.{LongWritable, Text}
import org.apache.hadoop.io.compress.CompressionCodecFactory
import org.apache.hadoop.mapreduce.lib.input.{FileInputFormat, FileSplit}
import org.apache.hadoop.mapreduce.{InputSplit, JobContext, RecordReader, TaskAttemptContext}

import java.io.{ByteArrayInputStream, InputStream, SequenceInputStream}
import java.nio.charset.StandardCharsets
import scala.collection.mutable.ArrayBuffer

/** Uncompressed splits replay the preceding XML prefix to recover lexical context, then emit
  * records owned by their split. This can incur cumulative prefix I/O across splits. Gzip uses one
  * split.
  */
object DblpPieces {
  final case class Piece(start: Long, xml: String, oversize: Boolean, byteLength: Long)

  def headerAndBody(in: InputStream, limit: Int): (DblpXml.Header, InputStream) = {
    val kept = ArrayBuffer.empty[Byte]
    var done = false
    while (kept.length < limit && !done) {
      val b = in.read()
      if (b < 0) done = true
      else {
        kept += b.toByte
        if (kept.length >= 5 && tailHasDblpClose(kept)) done = true
      }
    }
    val text = new String(kept.toArray, StandardCharsets.UTF_8)
    val marker = text.indexOf("<dblp")
    val prefix = if (marker >= 0) text.substring(0, marker) else text
    val header = DblpXml.header(prefix)
    val replay = new SequenceInputStream(new ByteArrayInputStream(kept.toArray), in)
    (header, replay)
  }

  private def tailHasDblpClose(kept: ArrayBuffer[Byte]): Boolean = {
    val from = math.max(0, kept.length - 80)
    val tail = new String(kept.slice(from, kept.length).toArray, StandardCharsets.UTF_8)
    val open = tail.indexOf("<dblp")
    open >= 0 && tail.indexOf('>', open) >= 0
  }
}

final class PosStream(in: InputStream) {
  private val pushed = new java.util.ArrayDeque[Int]
  var pos: Long = 0L

  def read(): Int =
    if (!pushed.isEmpty) {
      pos += 1
      pushed.removeLast()
    } else {
      val b = in.read()
      if (b >= 0) pos += 1
      b
    }

  def unread(b: Int): Unit = {
    pushed.addLast(b)
    pos -= 1
  }
}

object DblpSplitReader {
  final case class Open(at: Long, name: String, nameByteLength: Long)
  final case class Element(
      xml: String,
      oversize: Boolean,
      byteLength: Long,
      unterminated: Boolean,
      storedNameHighWater: Int = 0,
      malformed: Boolean = false
  )

  /** Names retained on the open-element stack. Further nesting is drained and marked oversize. */
  val MaxStoredNestingDepth = 64

  /** Bytes retained for one tag name. A longer name is not stored and the record is oversize. */
  val MaxStoredTagNameBytes = 256

  private val InnerNames: Set[String] = Set(
    "author",
    "editor",
    "title",
    "booktitle",
    "pages",
    "year",
    "journal",
    "volume",
    "number",
    "month",
    "url",
    "ee",
    "cite",
    "publisher",
    "note",
    "crossref",
    "isbn",
    "series",
    "school",
    "chapter",
    "address",
    "cdrom",
    "publnr",
    "sup",
    "sub",
    "i",
    "tt",
    "ref"
  )

  /** Start offset of record number `limit` (0-based), or `Long.MaxValue` when fewer records exist.
    * `limit <= 0` rejects every record. The scan does not retain record bodies.
    */
  def offsetAfter(stream: PosStream, limit: Int): Long = {
    if (limit <= 0) 0L
    else {
      var seen = 0
      var open = nextOpen(stream, Long.MaxValue)
      while (open.nonEmpty && seen < limit) {
        val found = open.get
        readElement(stream, found, 0L)
        seen += 1
        open = nextOpen(stream, Long.MaxValue)
      }
      if (seen < limit) Long.MaxValue else open.map(_.at).getOrElse(Long.MaxValue)
    }
  }

  /** First publication open at or after `start`. Earlier publications are drained and discarded.
    * The scan starts at the stream position, so a split reader begins at byte 0. Comment, CDATA,
    * and processing-instruction regions are skipped by the same rules as an unsplit read, including
    * when they began before `start`.
    */
  def firstAtOrAfter(stream: PosStream, start: Long): Option[Open] = {
    if (start <= 0) None
    else {
      var open = nextOpen(stream, Long.MaxValue)
      while (open.exists(_.at < start)) {
        val found = open.get
        readElement(stream, found, 0L)
        open = nextOpen(stream, Long.MaxValue)
      }
      open
    }
  }

  def nextOpen(stream: PosStream, end: Long): Option[Open] = {
    while (stream.pos < end) {
      val b = stream.read()
      if (b < 0) return None
      if (b == '<') {
        val at = stream.pos - 1L
        if (at >= end) return None
        classify(stream) match {
          case TagStart(name, length) if name == "dblp" && length == name.length =>
            skipStartTag(stream)
          case TagStart(name, length) if InnerNames.contains(name) && length == name.length =>
            readElement(stream, name, 0L)
          case TagStart(name, length) if name.nonEmpty =>
            return Some(Open(at, name, length))
          case _ => ()
        }
      }
    }
    None
  }

  /** Reads one element starting at the byte after `<name`. Comment, CDATA, and quoted text do not
    * change depth. EOF before the matching close is unterminated. A self-closing tag ends here.
    *
    * At most [[MaxStoredNestingDepth]] open names and [[MaxStoredTagNameBytes]] bytes of one tag
    * name are retained. After `maxBytes`, or when another stored name would exceed either cap, the
    * rest of the element is drained with the integer depth counter. A nesting or name-byte cap on a
    * record still within `maxBytes` sets `oversize` (callers reject it). This method does not
    * throw.
    */
  def readElement(stream: PosStream, open: Open, maxBytes: Long): Element =
    readElement(stream, open.name, maxBytes, open.nameByteLength)

  def readElement(
      stream: PosStream,
      name: String,
      maxBytes: Long,
      openingNameBytes: Long = -1L
  ): Element = {
    val stored = new java.io.ByteArrayOutputStream
    val startBytes = ("<" + name.take(MaxStoredTagNameBytes)).getBytes(StandardCharsets.UTF_8)
    stored.write(startBytes)
    var total = 1L + (if (openingNameBytes < 0) name.length.toLong else openingNameBytes)
    var oversize = total > maxBytes || total - 1L > MaxStoredTagNameBytes
    var draining = oversize
    var depth = 1
    var state = State.StartTag
    var slash = false
    var unterminated = false
    var malformed = false
    val nameBuf = new java.io.ByteArrayOutputStream
    val openNames = ArrayBuffer(name.take(MaxStoredTagNameBytes))
    var storedNameHighWater = openNames.length
    var pendingEnd = ""

    def startDraining(): Unit = {
      draining = true
      oversize = true
      nameBuf.reset()
    }

    def store(b: Int): Boolean = {
      total += 1
      if (!oversize && stored.size() < maxBytes) {
        stored.write(b)
        true
      } else {
        startDraining()
        false
      }
    }

    def unstore(kept: Boolean): Unit = {
      total -= 1
      if (kept && stored.size() > 0) {
        val raw = stored.toByteArray
        stored.reset()
        stored.write(raw, 0, raw.length - 1)
      }
    }

    def finishName(): String = {
      val text = new String(nameBuf.toByteArray, StandardCharsets.UTF_8)
      nameBuf.reset()
      text
    }

    def rememberStart(child: String): Unit = {
      openNames += child
      if (openNames.length > storedNameHighWater) storedNameHighWater = openNames.length
    }

    var closed = false
    while (!closed) {
      val b = stream.read()
      if (b < 0) {
        unterminated = depth > 0
        closed = true
      } else {
        val kept = store(b)
        state match {
          case State.StartTag =>
            if (b == '"') state = State.DQuote
            else if (b == '\'') state = State.SQuote
            else if (b == '/') slash = true
            else if (b == '>') {
              if (slash && !draining && openNames.nonEmpty) openNames.remove(openNames.length - 1)
              if (slash) {
                depth -= 1
                if (depth == 0) closed = true
              }
              slash = false
              state = State.Text
            } else slash = false
          case State.DQuote =>
            if (b == '"') state = State.StartTag
          case State.SQuote =>
            if (b == '\'') state = State.StartTag
          case State.Text =>
            if (b == '<') state = State.Lt
          case State.Lt =>
            if (b == '!') state = State.Bang
            else if (b == '?') state = State.Pi
            else if (b == '/') {
              nameBuf.reset()
              state = State.EndName
            } else if (isNameByte(b)) {
              nameBuf.reset()
              if (!draining) nameBuf.write(b)
              state = State.StartName
            } else {
              malformed = true
              state = State.Text
            }
          case State.StartName =>
            if (isNameByte(b)) {
              if (!draining && nameBuf.size() < MaxStoredTagNameBytes) nameBuf.write(b)
              else if (!draining) startDraining()
            } else {
              if (!draining && openNames.length < MaxStoredNestingDepth) rememberStart(finishName())
              else startDraining()
              depth += 1
              unstore(kept)
              stream.unread(b)
              slash = false
              state = State.StartTag
            }
          case State.EndName =>
            if (isNameByte(b)) {
              if (!draining && nameBuf.size() < MaxStoredTagNameBytes) nameBuf.write(b)
              else if (!draining) startDraining()
            } else {
              if (!draining) {
                pendingEnd = finishName()
                if (pendingEnd.isEmpty) malformed = true
              } else nameBuf.reset()
              unstore(kept)
              stream.unread(b)
              state = State.EndTag
            }
          case State.EndTag =>
            if (b == '>') {
              val matches = !draining && openNames.nonEmpty && openNames.last == pendingEnd
              if (draining || matches) {
                if (matches) openNames.remove(openNames.length - 1)
                if (depth > 0) depth -= 1
                if (depth == 0) closed = true
                else state = State.Text
              } else {
                malformed = true
                // A root close is also a safe recovery boundary for a malformed child stack.
                // Keep the reject flag, but do not consume the next publication as its body.
                if (openNames.nonEmpty && openNames.head == pendingEnd) {
                  depth = 0
                  closed = true
                } else state = State.Text
              }
            } else if (!isXmlWhitespace(b)) malformed = true
          case State.Bang =>
            if (b == '-') state = State.BangDash
            else if (b == '[') state = State.CdataOpen
            else {
              unstore(kept)
              stream.unread(b)
              state = State.Decl
            }
          case State.BangDash =>
            state = if (b == '-') State.Comment else State.Decl
          case State.Comment =>
            if (b == '-') state = State.CommentDash
          case State.CommentDash =>
            state = if (b == '-') State.CommentDash2 else State.Comment
          case State.CommentDash2 =>
            state =
              if (b == '>') State.Text else if (b == '-') State.CommentDash2 else State.Comment
          case State.CdataOpen =>
            state = if (b == 'C' || b == 'D' || b == 'A' || b == 'T' || b == '[') {
              if (b == '[') State.Cdata else State.CdataOpen
            } else State.Decl
          case State.Cdata =>
            if (b == ']') state = State.CdataEnd
          case State.CdataEnd =>
            state = if (b == ']') State.CdataEnd2 else State.Cdata
          case State.CdataEnd2 =>
            state = if (b == '>') State.Text else if (b == ']') State.CdataEnd2 else State.Cdata
          case State.Pi =>
            if (b == '?') state = State.PiEnd
          case State.PiEnd =>
            state = if (b == '>') State.Text else State.Pi
          case State.Decl =>
            if (b == '>') state = State.Text
            else if (b == '[') state = State.DeclBracket
          case State.DeclBracket =>
            if (b == ']') state = State.Decl
        }
      }
    }
    val bytes = stored.toByteArray
    val keptBytes = if (oversize) bytes.take(math.min(256, bytes.length)) else bytes
    Element(
      new String(keptBytes, StandardCharsets.UTF_8),
      oversize,
      total,
      unterminated,
      storedNameHighWater,
      malformed
    )
  }

  private sealed trait Tag
  private case object TagSkip extends Tag
  private final case class TagStart(name: String, byteLength: Long) extends Tag

  private def classify(stream: PosStream): Tag = {
    val first = stream.read()
    if (first < 0) TagSkip
    else if (first == '!') {
      skipDeclaration(stream)
      TagSkip
    } else if (first == '?') {
      skipUntil(stream, Array('?', '>'))
      TagSkip
    } else if (first == '/') {
      skipName(stream)
      skipStartTag(stream)
      TagSkip
    } else if (isNameByte(first)) {
      val bytes = new java.io.ByteArrayOutputStream
      bytes.write(first)
      var byteLength = 1L
      var continue = true
      while (continue) {
        val b = stream.read()
        if (b < 0) continue = false
        else if (isNameByte(b)) {
          byteLength += 1L
          if (bytes.size() < MaxStoredTagNameBytes) bytes.write(b)
        } else {
          stream.unread(b)
          continue = false
        }
      }
      TagStart(new String(bytes.toByteArray, StandardCharsets.UTF_8), byteLength)
    } else TagSkip
  }

  private def skipDeclaration(stream: PosStream): Unit = {
    val a = stream.read()
    val b = stream.read()
    if (a == '-' && b == '-') skipUntil(stream, Array('-', '-', '>'))
    else if (a == '[' && b == 'C') skipUntil(stream, Array(']', ']', '>'))
    else {
      if (b >= 0) stream.unread(b)
      if (a >= 0) stream.unread(a)
      var bracket = 0
      var closed = false
      while (!closed) {
        val c = stream.read()
        if (c < 0) closed = true
        else if (c == '[') bracket += 1
        else if (c == ']' && bracket > 0) bracket -= 1
        else if (c == '>' && bracket == 0) closed = true
      }
    }
  }

  private def skipStartTag(stream: PosStream): Unit = {
    var quote = 0
    var closed = false
    while (!closed) {
      val b = stream.read()
      if (b < 0) closed = true
      else if (quote == 0 && (b == '"' || b == '\'')) quote = b
      else if (quote != 0 && b == quote) quote = 0
      else if (quote == 0 && b == '>') closed = true
    }
  }

  private def skipName(stream: PosStream): Unit = {
    var continue = true
    while (continue) {
      val b = stream.read()
      if (b < 0 || !isNameByte(b)) {
        if (b >= 0) stream.unread(b)
        continue = false
      }
    }
  }

  private def skipUntil(stream: PosStream, marker: Array[Int]): Unit = {
    val window = ArrayBuffer.empty[Int]
    var closed = false
    while (!closed) {
      val b = stream.read()
      if (b < 0) closed = true
      else {
        window += b
        if (window.length > marker.length) window.remove(0)
        if (window.length == marker.length && window.indices.forall(i => window(i) == marker(i)))
          closed = true
      }
    }
  }

  private def isNameByte(b: Int): Boolean =
    (b >= 'A' && b <= 'Z') || (b >= 'a' && b <= 'z') || (b >= '0' && b <= '9') ||
      b == '_' || b == '-' || b == ':' || b == '.'

  private def isXmlWhitespace(b: Int): Boolean =
    b == ' ' || b == '\t' || b == '\r' || b == '\n'

  private object State {
    val StartTag = 0
    val DQuote = 1
    val SQuote = 2
    val Text = 3
    val Lt = 4
    val StartName = 5
    val EndName = 6
    val EndTag = 7
    val Bang = 8
    val BangDash = 9
    val Comment = 10
    val CommentDash = 11
    val CommentDash2 = 12
    val CdataOpen = 13
    val Cdata = 14
    val CdataEnd = 15
    val CdataEnd2 = 16
    val Pi = 17
    val PiEnd = 18
    val Decl = 19
    val DeclBracket = 20
  }
}

final class DblpXmlInputFormat extends FileInputFormat[LongWritable, Text] {
  override def createRecordReader(
      split: InputSplit,
      context: TaskAttemptContext
  ): RecordReader[LongWritable, Text] = new DblpXmlRecordReader

  override protected def isSplitable(context: JobContext, filename: HPath): Boolean = {
    val codec = new CompressionCodecFactory(context.getConfiguration).getCodec(filename)
    codec == null
  }
}

final class DblpXmlRecordReader extends RecordReader[LongWritable, Text] {
  private val currentKey = new LongWritable
  private val currentValue = new Text
  private var stream: PosStream = _
  private var raw: InputStream = _
  private var end = 0L
  private var header = DblpXml.Header(Map.empty, None)
  private var maxRecordBytes = Long.MaxValue
  private var progressStart = 0L
  private var progressEnd = 1L
  private var primed: Option[DblpSplitReader.Open] = None
  private var takePrimed = false

  override def initialize(split: InputSplit, context: TaskAttemptContext): Unit = {
    val fileSplit = split.asInstanceOf[FileSplit]
    val conf = context.getConfiguration
    maxRecordBytes = conf.getLong(ConfKeys.MaxRecordBytes, Long.MaxValue)
    val path = fileSplit.getPath
    val fs = path.getFileSystem(conf)
    val codec = new CompressionCodecFactory(conf).getCodec(path)
    if (codec != null) {
      val opened = fs.open(path)
      raw = codec.createInputStream(opened)
      val prepared = DblpPieces.headerAndBody(raw, 65536)
      header = prepared._1
      stream = new PosStream(prepared._2)
      end = Long.MaxValue
      progressStart = 0L
      progressEnd = math.max(1L, fs.getFileStatus(path).getLen)
    } else {
      val probe = fs.open(path)
      val prepared = DblpPieces.headerAndBody(probe, 65536)
      header = prepared._1
      prepared._2.close()
      val opened = fs.open(path)
      val begin = fileSplit.getStart
      raw = opened
      stream = new PosStream(raw)
      end = begin + fileSplit.getLength
      progressStart = begin
      progressEnd = math.max(begin + 1, end)
      if (begin > 0) {
        takePrimed = true
        primed = DblpSplitReader.firstAtOrAfter(stream, begin)
      }
    }
  }

  override def nextKeyValue(): Boolean = {
    val open =
      if (takePrimed) {
        takePrimed = false
        primed.filter(_.at < end)
      } else DblpSplitReader.nextOpen(stream, end)
    open match {
      case None => false
      case Some(found) =>
        val read = DblpSplitReader.readElement(stream, found, maxRecordBytes)
        currentKey.set(found.at)
        currentValue.set(encode(read))
        true
    }
  }

  override def getCurrentKey: LongWritable = currentKey
  override def getCurrentValue: Text = currentValue
  override def getProgress: Float =
    math.min(1f, (stream.pos - progressStart).toFloat / (progressEnd - progressStart).toFloat)

  override def close(): Unit =
    if (raw != null) raw.close()

  private def encode(read: DblpSplitReader.Element): String = {
    val meta = ujson.Obj(
      "unsafe" -> header.unsafe.map(ujson.Str(_)).getOrElse(ujson.Null),
      "entities" -> ujson.Obj.from(header.entities.map { case (k, v) => k -> ujson.Str(v) }),
      "oversize" -> read.oversize,
      "unterminated" -> read.unterminated,
      "malformed" -> read.malformed,
      "bytes" -> read.byteLength
    )
    ujson.write(meta) + "\n" + read.xml
  }
}

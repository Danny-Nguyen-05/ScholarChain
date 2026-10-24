package edu.uic.cs441.scholarchain.storage

import java.nio.file.{Files, Path, StandardOpenOption}
import java.nio.charset.StandardCharsets.UTF_8
import java.security.MessageDigest
import java.io.{Reader, PushbackReader}
import scala.collection.mutable
import scala.jdk.CollectionConverters.*

private[storage] object ExportFiles {
  def hash(text: String): String = StorageKeys.sha256(text.getBytes(UTF_8).toVector)
  def canonical(row: ujson.Obj): String =
    ujson.Obj.from(row.obj.toVector.filterNot(_._1 == "run_id").sortBy(_._1)).render()
  def deleteTree(root: Path): Unit = {
    val walk = Files.walk(root);
    try
      walk
        .sorted(java.util.Comparator.reverseOrder[Path]())
        .iterator()
        .asScala
        .foreach(Files.deleteIfExists)
    finally walk.close()
  }
  def append(path: Path, text: String): Unit = Files.writeString(
    path,
    text + "\n",
    UTF_8,
    StandardOpenOption.CREATE,
    StandardOpenOption.APPEND
  )
}

/** The 256 shard streams and merge rounds retain at most chunkRows row strings and 64 merge heads.
  */
private[storage] final class SpillDigest(root: Path, chunkRows: Int) {
  import ExportFiles.*
  Files.createDirectories(root)
  private val counts = mutable.Map.empty[String, Long].withDefaultValue(0L)
  var rowCount: Long = 0L
  def add(row: ujson.Obj): Unit = {
    val json = canonical(row); val shard = hash(json).take(2);
    append(root.resolve("shard-" + shard), json); counts(shard) += 1; rowCount += 1
  }
  private def compare(a: String, b: String): Int = {
    val x = a.getBytes(UTF_8); val y = b.getBytes(UTF_8); var i = 0
    while (i < math.min(x.length, y.length)) {
      val d = (x(i) & 255) - (y(i) & 255); if (d != 0) return d; i += 1
    }; x.length - y.length
  }
  private def shard(path: Path): String = {
    var count = 0
    val input = Files.newBufferedReader(path, UTF_8)
    try {
      var end = false
      while (!end) {
        val chunk = mutable.ArrayBuffer.empty[String];
        while (chunk.size < chunkRows && !end) {
          val l = input.readLine(); if (l == null) end = true else chunk += l
        };
        if (chunk.nonEmpty) {
          Files.write(
            root.resolve("chunk-" + count),
            chunk.sortWith((a, b) => compare(a, b) < 0).asJava,
            UTF_8
          ); count += 1
        }
      }
    } finally input.close()
    def part(round: Int, i: Int) = root.resolve(if (round < 0) "chunk-" + i else s"merge-$round-$i")
    def merge(inputs: Vector[Path], out: Option[Path]): String = {
      val readers = inputs.map(p => Files.newBufferedReader(p, UTF_8));
      val writer = out.map(p => Files.newBufferedWriter(p, UTF_8))
      val queue =
        new java.util.PriorityQueue[(String, Int)](new java.util.Comparator[(String, Int)] {
          def compare(a: (String, Int), b: (String, Int)) = SpillDigest.this.compare(a._1, b._1)
        })
      val digest = MessageDigest.getInstance("SHA-256")
      try {
        readers.zipWithIndex.foreach((r, i) =>
          Option(r.readLine()).foreach(s => queue.add(s -> i))
        ); var first = true
        while (!queue.isEmpty) {
          val (s, i) = queue.remove(); if (!first) digest.update('\n'.toByte); first = false;
          digest.update(s.getBytes(UTF_8)); writer.foreach(w => { w.write(s); w.newLine() });
          Option(readers(i).readLine()).foreach(v => queue.add(v -> i))
        }
        digest.digest().map(b => f"${b & 255}%02x").mkString
      } finally { readers.foreach(_.close()); writer.foreach(_.close()) }
    }
    var round = -1
    while (count > 64) {
      val next = (count + 63) / 64; var n = 0;
      while (n < next) {
        val ins = (n * 64 until math.min(count, (n + 1) * 64)).map(i => part(round, i)).toVector;
        merge(ins, Some(part(round + 1, n))); ins.foreach(Files.delete); n += 1
      }; count = next; round += 1
    }
    val ins = (0 until count).map(i => part(round, i)).toVector; val result = merge(ins, None);
    ins.foreach(Files.delete); result
  }
  def finish(): String = {
    val lines =
      counts.toVector.sortBy(_._1).map((s, n) => s"$s:$n:${shard(root.resolve("shard-" + s))}");
    hash("sha256-fixed-256-shard-sorted-row-json-merkle-v1\n" + lines.mkString("\n"))
  }
}
private[storage] final case class CsvCell(text: String, quoted: Boolean)

/** RFC4180 stream preserving embedded CR/LF and empty quoted strings versus null cells. */
private[storage] final class CsvRecords(input: Reader, maxCellChars: Int) extends AutoCloseable {
  private val reader = new PushbackReader(input, 2)
  def next(): Option[Vector[CsvCell]] = {
    val fields = Vector.newBuilder[CsvCell]; val cell = new StringBuilder
    var fieldCount = 0; var inside = false; var quoted = false; var afterQuote = false;
    var began = false;
    var complete = false
    def append(c: Char): Unit = {
      cell.append(c); if (cell.length > maxCellChars) throw SourceRejected("csv-cell-limit")
    }
    def field(): Unit = {
      fieldCount += 1; if (fieldCount > 32) throw SourceRejected("csv-column-limit")
      fields += CsvCell(cell.toString, quoted); cell.clear(); quoted = false; afterQuote = false
    }
    while (!complete) {
      val raw = reader.read();
      if (raw < 0) {
        if (inside) throw SourceRejected("malformed-csv"); if (!began) return None; field();
        complete = true
      } else {
        began = true; val c = raw.toChar
        if (inside) {
          if (c == '"') {
            val peek = reader.read();
            if (peek == '"') append('"')
            else { inside = false; afterQuote = true; if (peek >= 0) reader.unread(peek) }
          } else append(c)
        } else
          c match {
            case '"' if cell.isEmpty && !afterQuote => inside = true; quoted = true
            case ','                                => field()
            case '\r' =>
              val peek = reader.read(); if (peek != '\n' && peek >= 0) reader.unread(peek); field();
              complete = true
            case '\n'            => field(); complete = true
            case _ if afterQuote => throw SourceRejected("malformed-csv")
            case _               => append(c)
          }
      }
    }
    Some(fields.result())
  }
  def close(): Unit = reader.close()
}

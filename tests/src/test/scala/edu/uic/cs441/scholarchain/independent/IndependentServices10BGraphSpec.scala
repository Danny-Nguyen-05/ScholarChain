package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.services.*
import edu.uic.cs441.scholarchain.storage.*
import java.util.concurrent.{CountDownLatch, TimeUnit}
import org.scalatest.funsuite.AnyFunSuite

class IndependentServices10BGraphSpec extends AnyFunSuite {
  import IndependentServices10BFixture.*
  private val context = RequestContext("request-graph-10b", "trace-graph-10b")
  private val cfg = GraphApiConfig(cursorKey = "synthetic-stable-cursor-key-10b")
  private def value(result: Either[ApiError, ApiReply]): ujson.Value =
    result.fold(e => fail(e.code), _.body)
  private def error(result: Either[ApiError, ApiReply], status: Int): Unit =
    assert(result.left.toOption.exists(_.status == status), result.toString)

  test(
    "directed graph exploration honors in/out/both, edge types and depth against literal topology"
  ) {
    val api = new GraphApi(snapshot(), cfg)
    try {
      def neighbors(id: String, params: (String, String)*) =
        value(api.neighbors(id, params.toMap, context))("items").arr.toVector
      assert(neighbors(a, "direction" -> "out").map(_("nodeId").str).toSet == Set(work1, work2))
      assert(neighbors(a, "direction" -> "in").isEmpty)
      assert(neighbors(work1, "direction" -> "in").map(_("nodeId").str).toSet == Set(a, b))
      val authored = neighbors(a, "direction" -> "both", "depth" -> "2", "edgeTypes" -> "AUTHORED")
      assert(authored.map(_("edgeId").str).toSet == graphEdges.take(3).map(_.edgeId).toSet)
      assert(!authored.exists(_("nodeId").str == topic))
      val twoHops = neighbors(a, "direction" -> "out", "depth" -> "2")
      assert(twoHops.map(_("nodeId").str).toSet == Set(work1, work2, topic))
      assert(twoHops.find(_("nodeId").str == topic).get("depth").num == 2)
      assert(value(api.node(a, context))("nodeId").str == a)
      error(api.node("missing-node", context), 404)
    } finally api.close()
  }

  test(
    "signed pagination replays stably and rejects tampering, changed filters, node or snapshot"
  ) {
    val api = new GraphApi(snapshot(), cfg)
    val otherSnapshot = new GraphApi(snapshot("synthetic-10b-snapshot-v2"), cfg)
    try {
      val params = Map("direction" -> "out", "limit" -> "1")
      val first = value(api.neighbors(a, params, context))
      val cursor = first("cursor").str
      assert(cursor.nonEmpty && first("items").arr.size == 1)
      val next = params.updated("cursor", cursor)
      val second = value(api.neighbors(a, next, context))
      assert(second == value(api.neighbors(a, next, context)))
      assert(second("cursor") == ujson.Null)
      val nodes = first("items").arr.toVector ++ second("items").arr.toVector
      assert(nodes.map(_("nodeId").str).toSet == Set(work1, work2))
      assert(nodes.map(_("edgeId").str).distinct.size == 2)
      for (
        changed <- Vector(
          next.updated("direction", "both"),
          next.updated("depth", "2"),
          next.updated("limit", "2"),
          next.updated("edgeTypes", "AUTHORED"),
          next.updated("cursor", cursor + "x")
        )
      ) error(api.neighbors(a, changed, context), 400)
      error(api.neighbors(b, next, context), 400)
      error(otherSnapshot.neighbors(a, next, context), 400)
    } finally { api.close(); otherSnapshot.close() }
  }

  test("graph request caps reject unbounded or unsupported work before retrieval") {
    val api = new GraphApi(snapshot(), cfg)
    val scanCap = new GraphApi(snapshot(), cfg.copy(maxScannedEdges = 1))
    val nodeCap = new GraphApi(snapshot(), cfg.copy(maxVisitedNodes = 1))
    try {
      for (
        params <- Vector(
          Map("depth" -> "0"),
          Map("depth" -> "4"),
          Map("depth" -> "1.5"),
          Map("limit" -> "0"),
          Map("limit" -> "201"),
          Map("direction" -> "sideways"),
          Map("edgeTypes" -> "UNDECLARED"),
          Map("timeoutMs" -> "0"),
          Map("timeoutMs" -> "5001"),
          Map("unknown" -> "ignored")
        )
      ) error(api.neighbors(a, params, context), 400)
      error(scanCap.neighbors(a, Map.empty, context), 422)
      error(nodeCap.neighbors(a, Map.empty, context), 422)
    } finally { api.close(); scanCap.close(); nodeCap.close() }
  }

  test("hard aggregate graph timeout interrupts a blocked snapshot adapter") {
    val entered = new CountDownLatch(1)
    val interrupted = new CountDownLatch(1)
    val delegate = snapshot()
    val slow = new GraphSnapshot {
      def snapshotId = delegate.snapshotId
      def node(id: String) = delegate.node(id)
      def edges(id: String, window: String): StorageResult[Vector[GraphEdge]] = {
        entered.countDown()
        try { Thread.sleep(10000); delegate.edges(id, window) }
        catch {
          case _: InterruptedException => interrupted.countDown(); throw new InterruptedException
        }
      }
      def metrics(id: String, window: String) = delegate.metrics(id, window)
    }
    val api = new GraphApi(slow, cfg.copy(timeoutMs = 50))
    try {
      val start = System.nanoTime()
      error(api.neighbors(a, Map.empty, context), 504)
      assert(entered.await(1, TimeUnit.SECONDS))
      assert(interrupted.await(1, TimeUnit.SECONDS))
      assert(TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start) < 2000)
    } finally api.close()
  }
}

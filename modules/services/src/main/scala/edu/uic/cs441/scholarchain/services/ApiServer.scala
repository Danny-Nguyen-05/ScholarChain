package edu.uic.cs441.scholarchain.services

import io.undertow.Undertow
import java.net.InetSocketAddress
import scala.jdk.CollectionConverters.*
import scala.util.control.NonFatal

/** Transport adapters only read bounded wire input and delegate to the application. */
object ApiServer {
  final class RunningServer private[services] (
      server: Undertow,
      main: cask.Main,
      app: ApiApplication
  ) extends AutoCloseable {
    def port: Int = server.getListenerInfo.get(0).getAddress.asInstanceOf[InetSocketAddress].getPort
    def close(): Unit = { server.stop(); main.executionContext.shutdown(); app.close() }
  }
  def start(
      app: ApiApplication,
      host: String = "127.0.0.1",
      port: Int = 0,
      maxRequestBytes: Int = 0
  ): RunningServer = {
    val byteLimit = if (maxRequestBytes > 0) maxRequestBytes else app.requestByteLimit
    val main = new cask.Main {
      override def debugMode = false
      val allRoutes = Seq(new cask.Routes {
        @cask.route(
          "/",
          methods = Seq("get", "post", "put", "delete", "patch", "head", "options", "trace")
        )
        def dispatch(
            request: cask.Request,
            remaining: cask.RemainingPathSegments,
            params: cask.QueryParams
        ): cask.Response[String] = {
          val exchange = request.exchange
          val headers = exchange.getRequestHeaders.asScala
            .map(h => h.getHeaderName.toString -> h.getFirst)
            .toMap
          val body =
            try {
              val bytes = exchange.getInputStream.readNBytes(byteLimit + 1)
              if (bytes.length > byteLimit) Left(ApiError.invalid)
              else Right(new String(bytes, java.nio.charset.StandardCharsets.UTF_8))
            } catch { case NonFatal(_) => Left(ApiError.invalid) }
          val result = app.handle(
            exchange.getRequestMethod.toString,
            exchange.getRequestPath + Option(exchange.getQueryString)
              .filter(_.nonEmpty)
              .map("?" + _)
              .getOrElse(""),
            headers,
            body.getOrElse(""),
            body.left.toOption
          )
          cask.Response(result.body, statusCode = result.status, headers = result.headers.toSeq)
        }
        initialize()
      })
      override def handleMethodNotAllowed(req: cask.Request): cask.Response.Raw = fallback(req)
      override def handleNotFound(req: cask.Request): cask.Response.Raw = fallback(req)
      private def fallback(req: cask.Request): cask.Response.Raw = {
        val headers = req.exchange.getRequestHeaders.asScala
          .map(h => h.getHeaderName.toString -> h.getFirst)
          .toMap
        val result = app.handle(
          req.exchange.getRequestMethod.toString,
          req.exchange.getRequestPath + Option(req.exchange.getQueryString)
            .filter(_.nonEmpty)
            .map("?" + _)
            .getOrElse(""),
          headers,
          ""
        )
        cask.Response(result.body, statusCode = result.status, headers = result.headers.toSeq)
      }
    }
    val server = Undertow
      .builder()
      .addHttpListener(port, host)
      .setSocketOption(
        org.xnio.Options.READ_TIMEOUT,
        java.lang.Integer.valueOf(app.requestReadTimeoutMs)
      )
      .setHandler(main.defaultHandler)
      .build()
    server.start()
    new RunningServer(server, main, app)
  }
}

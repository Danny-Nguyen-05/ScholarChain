package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.storage.InMemoryQuerySessionStore

/** 10A entrypoints are an offline foundation. No SDK, provider, credential discovery or production
  * backend is implicitly enabled. 10B supplies graph/semantic/worker composition.
  */
object ServiceBootstrap {
  def start(role: String): Unit = ServiceConfig.fromEnvironment(sys.env) match {
    case Left(code) => System.err.println(code)
    case Right(config) =>
      val unconfigured = new QueryWorkflow {
        def run(
            request: QueryRequest,
            context: RequestContext,
            stage: String => Unit
        ): Either[ApiError, WorkflowOutput] = Left(ApiError.unavailable)
      }
      val queries = new QueryService(new InMemoryQuerySessionStore, unconfigured, config)
      val app = new ApiApplication(queries, config, readiness = () => false, serviceRole = role)
      val server = ApiServer.start(app, config.host, config.port, config.maxRequestBytes)
      Runtime.getRuntime.addShutdownHook(new Thread(() => server.close()))
  }
}
object QueryApiMain { def main(args: Array[String]): Unit = ServiceBootstrap.start("query-api") }
object GraphServiceMain {
  def main(args: Array[String]): Unit = ServiceBootstrap.start("graph-service")
}
object SemanticServiceMain {
  def main(args: Array[String]): Unit = ServiceBootstrap.start("semantic-service")
}
object EmbeddingWorkerMain {
  def main(args: Array[String]): Unit = ServiceBootstrap.start("embedding-worker")
}

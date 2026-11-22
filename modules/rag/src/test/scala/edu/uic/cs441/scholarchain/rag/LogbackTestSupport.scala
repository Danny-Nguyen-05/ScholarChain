package edu.uic.cs441.scholarchain.rag

import ch.qos.logback.classic.spi.ILoggingEvent
import ch.qos.logback.classic.{Level, LoggerContext}
import ch.qos.logback.core.read.ListAppender
import org.slf4j.LoggerFactory
import scala.jdk.CollectionConverters.*

/** Captures the formatted messages of one logger while a body runs.
  *
  * Why the level is forced: the scripted `check` exports a logback configuration whose root level
  * is WARN (docs/agent-runs/phase-04/xml-repair-logback.xml), while plain `sbt` falls back to
  * logback's DEBUG default. The runtime stage events are logged at INFO, so a capture that never
  * sets the logger's level sees nothing under the check script and everything under plain `sbt`.
  * Setting the level on the captured logger itself makes the capture independent of that
  * configuration. The previous level is restored and the appender stopped afterwards.
  *
  * Test suites in this module run sequentially (`Test / parallelExecution := false`), so no lock is
  * needed against other rag suites.
  */
object LogbackTestSupport {

  /** Messages logged to `loggerName` while `body` runs, with the logger set to `level`. */
  def capture(loggerName: String, level: Level = Level.INFO)(body: => Unit): Vector[String] = {
    val context = LoggerFactory.getILoggerFactory.asInstanceOf[LoggerContext]
    val logger = context.getLogger(loggerName)
    val appender = new ListAppender[ILoggingEvent]
    appender.setContext(context)
    appender.start()
    val previous = logger.getLevel
    logger.addAppender(appender)
    logger.setLevel(level)
    try body
    finally {
      logger.detachAppender(appender)
      logger.setLevel(previous)
      appender.stop()
    }
    appender.synchronized(appender.list.asScala.toVector).map(_.getFormattedMessage)
  }
}

package scholarchain.build

/** Guard used by tests; production check pipeline must not invoke markTestRun after failures. */
object TestRunMarkerPolicy {
  private[build] var shouldSkipWriteAfterFailedChecks: Boolean = false

  def withFailedChecksGuard[T](failedChecks: Boolean)(body: => T): T =
    if (failedChecks) {
      shouldSkipWriteAfterFailedChecks = true
      try body
      finally shouldSkipWriteAfterFailedChecks = false
    } else body
}

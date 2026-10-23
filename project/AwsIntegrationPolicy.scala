package scholarchain.build

object AwsIntegrationPolicy {
  val tag = "edu.uic.cs441.scholarchain.storage.AwsIntegration"

  def requireEnabled(environment: Map[String, String]): Unit = {
    require(
      environment.get("SCHOLARCHAIN_AWS_ITEST").contains("1"),
      "awsIntegration is disabled; set SCHOLARCHAIN_AWS_ITEST=1 only for an approved live test run"
    )
    require(
      environment.get("AWS_PROFILE").exists(_.trim.nonEmpty),
      "awsIntegration requires an explicit nonblank AWS_PROFILE"
    )
  }
}

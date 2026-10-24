package edu.uic.cs441.scholarchain.storage

import software.amazon.awssdk.services.neptunedata.NeptunedataClient
import software.amazon.awssdk.services.neptunedata.model.{
  StartLoaderJobRequest,
  GetLoaderJobStatusRequest
}
import software.amazon.awssdk.awscore.AwsRequestOverrideConfiguration
import java.time.Duration
import java.nio.file.Files
import java.nio.charset.StandardCharsets.UTF_8
import scala.jdk.CollectionConverters.*
import StorageResult.*

final class NeptuneGraphLoader(
    client: NeptunedataClient,
    objects: ObjectStore,
    ledger: RunLedger,
    registry: ArtifactRegistry,
    config: NeptuneLoaderConfig,
    validator: NeptuneExportValidator,
    sleep: Long => Unit = ms => Thread.sleep(ms),
    nowMillis: () => Long = () => System.nanoTime() / 1000000L
) extends GraphLoader {
  private val retry = new StorageRetry(config.retry, sleep)
  private def timeout = AwsRequestOverrideConfiguration
    .builder()
    .apiCallTimeout(Duration.ofMillis(config.requestTimeoutMillis))
    .build()
  def status(loadId: String): StorageResult[GraphLoadStatus] = {
    if (loadId.isEmpty) return Rejected("invalid-load-id")
    retry {
      val response = client.getLoaderJobStatus(
        GetLoaderJobStatusRequest
          .builder()
          .loadId(loadId)
          .details(false)
          .errors(false)
          .overrideConfiguration(timeout)
          .build()
      )
      try {
        val payload = AwsDocumentJson.value(response.payload());
        Found(GraphLoadStatus(loadId, payload("overallStatus")("status").str))
      } catch { case _: Exception => Rejected("malformed-loader-status") }
    }
  }
  def submitBulkLoad(manifest: GraphLoadManifest): StorageResult[GraphLoadStatus] = {
    RowCodec.map(validator.validate(manifest))(loadValidated)
  }
  private[storage] def loadValidated(
      validated: ValidatedNeptuneExport
  ): StorageResult[GraphLoadStatus] = {
    val manifest = GraphLoadManifest(validated.runId, validated.root.toString, "opencypher")
    try {
      val completeId = "neptune-complete:" + manifest.runId
      registry.get(completeId, validated.fingerprint) match {
        case Found(record) => return Unchanged(GraphLoadStatus(record.uri, "LOAD_COMPLETED"))
        case Missing       => ()
        case _             => return Rejected("neptune-registry-unavailable")
      }
      val run = "neptune:" + manifest.runId + ":" + validated.fingerprint
      if (!StorageResult.successful(ledger.startRun(run))) return Rejected("ledger-start-failed")
      if (!StorageResult.successful(ledger.recordStage(run, "bulk-load")))
        return Rejected("ledger-stage-failed")
      def fail(code: String): StorageResult[GraphLoadStatus] = {
        val count = StorageResult
          .value(ledger.getRun(run))
          .toVector
          .flatMap(_.stages)
          .find(_.stageKey == "bulk-load")
          .map(_.retryCount + 1)
          .getOrElse(1)
        ledger.recordFailure(run, "bulk-load", count, code)
        Rejected(code)
      }
      val base = StorageKeys.versioned(config.graphPrefix, validated.fingerprint, "validated")
      var uploadFailure: Option[String] = None
      validated.foreachObject { (path, relative) =>
        if (uploadFailure.isEmpty) {
          if (Files.size(path) > config.maxUploadBytes)
            uploadFailure = Some("graph-upload-size-limit")
          else {
            val bytes = Files.readAllBytes(path).toVector
            val result = objects.put(
              base + "/" + relative,
              bytes,
              if (relative.endsWith(".csv")) "text/csv" else "application/octet-stream",
              Map("run-id" -> manifest.runId)
            )
            if (!StorageResult.successful(result)) uploadFailure = Some("graph-upload-failed")
          }
        }
      }
      if (uploadFailure.nonEmpty) return fail(uploadFailure.get)
      val loadSource =
        "s3://" + config.bucket + "/" + base + "/" + validated.loaderRelativePrefix + "/"
      val loadManifest = ujson
        .Obj(
          "runId" -> manifest.runId,
          "fingerprint" -> validated.fingerprint,
          "source" -> loadSource,
          "nodeCount" -> validated.nodeCount,
          "edgeCount" -> validated.edgeCount,
          "supportCount" -> validated.supportCount,
          "sourceSupportPrefix" -> ("s3://" + config.bucket + "/" + base + "/edges/type=coauthored_with_support/")
        )
        .render()
      val published = objects.put(
        base + "/storage-load-manifest.json",
        loadManifest.getBytes(UTF_8).toVector,
        "application/json",
        Map("run-id" -> manifest.runId)
      )
      if (!StorageResult.successful(published)) return fail("graph-manifest-upload-failed")
      val attempts = new NeptuneJobAttempts(registry, manifest.runId, validated.fingerprint)
      val selected = StorageResult
        .value(attempts.select())
        .getOrElse(return fail("loader-job-registry-unavailable"))
      val loadId = selected.loadId.getOrElse {
        val submitted = retry {
          val response = client.startLoaderJob(
            StartLoaderJobRequest
              .builder()
              .source(loadSource)
              .format("opencypher")
              .s3BucketRegion(config.region)
              .iamRoleArn(config.iamRoleArn)
              .mode(if (selected.recovery) "NEW" else "AUTO")
              .failOnError(true)
              .userProvidedEdgeIds(true)
              .parallelism("LOW")
              .queueRequest(false)
              .overrideConfiguration(timeout)
              .build()
          )
          Option(response.payload().get("loadId"))
            .filter(_.nonEmpty)
            .map(Found(_))
            .getOrElse(Rejected("malformed-loader-submission"))
        }
        val id = StorageResult.value(submitted).getOrElse(return fail("neptune-submit-failed"))
        if (!StorageResult.successful(attempts.recordJob(selected, id)))
          return fail("loader-job-registry-failed")
        id
      }
      val started = nowMillis(); var polls = 0
      while (polls < config.maxPolls && nowMillis() - started < config.timeoutMillis) {
        val current = status(loadId)
        StorageResult.value(current) match {
          case Some(s) if s.state == "LOAD_COMPLETED" =>
            if (
              !StorageResult.successful(
                registry
                  .register(completeId, validated.fingerprint, loadId, validated.fingerprint)
              )
            ) return fail("loader-completion-registry-failed")
            if (
              !StorageResult.successful(ledger.completeStage(run, "bulk-load")) || !StorageResult
                .successful(ledger.completeRun(run))
            ) return Rejected("ledger-completion-failed")
            return Written(s)
          case Some(s) if NeptuneLoadStates.pending(s.state) => ()
          case Some(s) =>
            if (!StorageResult.successful(attempts.recordFailure(selected, s.state)))
              return fail("loader-failure-registry-failed")
            return fail(NeptuneLoadStates.failureCode(s.state))
          case None => return fail("neptune-status-failed")
        }
        polls += 1
        if (polls < config.maxPolls) {
          val remaining = config.timeoutMillis - (nowMillis() - started);
          if (remaining > 0) sleep(math.min(config.pollIntervalMillis, remaining))
        }
      }
      fail("neptune-load-timeout")
    } catch {
      case _: InterruptedException => Thread.currentThread().interrupt(); Rejected("interrupted")
    } finally validated.close()
  }
}

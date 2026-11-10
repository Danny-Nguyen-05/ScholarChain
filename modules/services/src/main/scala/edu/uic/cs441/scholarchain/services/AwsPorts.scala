package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.{EmbeddingClient, EmbeddingModel, RuntimeConfig}
import edu.uic.cs441.scholarchain.rag.{
  BedrockConverseLlmClient,
  BedrockEmbeddingClient,
  BedrockEmbeddingConfig,
  EmbeddingClientFactory,
  EmbeddingInputType,
  EmbeddingPricing,
  EmbeddingProvider,
  EmbeddingSpendCounter,
  LlmClient,
  SynthesisClients,
  SynthesisProvider,
  VoyageEmbeddingConfig
}
import edu.uic.cs441.scholarchain.storage.{
  ArtifactRegistry,
  DynamoArtifactRegistry,
  DynamoEntityLinkCache,
  DynamoEvidenceBundleStore,
  DynamoQuerySessionStore,
  DynamoResearcherMetricStore,
  DynamoRunLedger,
  EmbeddingQueueConfig,
  EmbeddingWorkQueue,
  EntityLinkCache,
  EvidenceBundleStore,
  DirectedGraphReader,
  GraphReaderConfig,
  IndexedEvidenceBundleStore,
  NeptuneGraphReader,
  ObjectStore,
  ObjectStoreRuntimeArtifactStore,
  ObjectStoreRuntimeAuditStore,
  QuerySessionStore,
  ResearcherMetricStore,
  RetryConfig,
  RunLedger,
  RuntimeArtifactPointer,
  RuntimeArtifactStore,
  RuntimeAuditStore,
  RuntimeAuditStoreConfig,
  S3ObjectStore,
  S3VectorStore,
  SqsEmbeddingWorkQueue,
  VectorAdapterConfig,
  VectorStore,
  StorageConfig as StoreConfig
}
import java.net.URI
import java.time.Duration
import scala.util.control.NonFatal
import software.amazon.awssdk.auth.credentials.{AwsCredentialsProvider, DefaultCredentialsProvider}
import software.amazon.awssdk.core.client.config.ClientOverrideConfiguration
import software.amazon.awssdk.awscore.retry.AwsRetryStrategy
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.s3.S3Client
import software.amazon.awssdk.services.s3vectors.S3VectorsClient
import software.amazon.awssdk.services.sqs.SqsClient

/** Ports each role composes from. The composition code sees only these storage and runtime ports;
  * the SDK client lifecycle is owned by the factory and released through close().
  */
sealed abstract class PortBundle(onClose: () => Unit) extends AutoCloseable {
  def close(): Unit = onClose()
}
final class GraphPorts(
    val reader: DirectedGraphReader,
    val metrics: ResearcherMetricStore,
    onClose: () => Unit = () => ()
) extends PortBundle(onClose)
final class SemanticPorts(
    val embedding: EmbeddingClient,
    val vectors: VectorStore,
    onClose: () => Unit = () => ()
) extends PortBundle(onClose)
final class QueryPorts(
    val sessions: QuerySessionStore,
    val evidence: EvidenceBundleStore,
    val audits: RuntimeAuditStore,
    val links: EntityLinkCache,
    val metrics: ResearcherMetricStore,
    val objects: ObjectStore,
    val artifacts: RuntimeArtifactStore,
    val llm: LlmClient,
    onClose: () => Unit = () => ()
) extends PortBundle(onClose)
final class WorkerPorts(
    val queue: EmbeddingWorkQueue,
    val dlq: EmbeddingWorkQueue,
    val sessions: QuerySessionStore,
    val objects: ObjectStore,
    val vectors: VectorStore,
    val registry: ArtifactRegistry,
    val ledger: RunLedger,
    val embedder: EmbeddingClient,
    onClose: () => Unit = () => ()
) extends PortBundle(onClose)

/** Creates the role's ports. A refusal is a closed code, never a provider message. */
trait AwsPortFactory {
  def graph(config: GraphRoleConfig): Either[String, GraphPorts]
  def semantic(config: SemanticRoleConfig): Either[String, SemanticPorts]
  def query(config: QueryRoleConfig, runtime: RuntimeConfig): Either[String, QueryPorts]
  def worker(config: WorkerRoleConfig): Either[String, WorkerPorts]
}

final case class OpenedGraphReader(reader: DirectedGraphReader, close: () => Unit)

/** Seam for the storage-owned read-only graph adapter. The runtime must not hold a raw graph SDK
  * client, so the client is created only inside the storage module. Tests inject a fake.
  */
trait GraphReaderProvider {
  def open(
      endpoint: URI,
      region: String,
      credentials: AwsCredentialsProvider,
      timeoutMs: Long
  ): Either[String, OpenedGraphReader]
}

/** Opens the storage-owned read-only graph reader. Storage builds and owns the SDK client, so this
  * module never names it. Construction makes no network call. Each storage refusal code becomes a
  * closed message that names a configuration variable or a missing capability, never a value.
  */
object StorageGraphReaderProvider extends GraphReaderProvider {
  val connectFailed = "graph-reader-connect-failed"
  private[services] def refusal(code: String): String = code match {
    case "invalid-neptune-endpoint" => "invalid-aws-configuration:SCHOLARCHAIN_NEPTUNE_ENDPOINT"
    case "invalid-neptune-region"   => "invalid-aws-configuration:AWS_REGION"
    case "missing-credentials"      => "aws-credentials-unavailable"
    case _                          => connectFailed
  }
  def open(
      endpoint: URI,
      region: String,
      credentials: AwsCredentialsProvider,
      timeoutMs: Long
  ): Either[String, OpenedGraphReader] =
    NeptuneGraphReader.connect(
      endpoint,
      region,
      credentials,
      GraphReaderConfig(requestTimeoutMillis = timeoutMs)
    ) match {
      case Left(code)    => Left(refusal(code))
      case Right(reader) => Right(OpenedGraphReader(reader, () => reader.close()))
    }
}

/** Seam for the external, non-AWS provider clients. The services module names only the narrow
  * ports; the rag-owned HTTP clients are adapted behind this trait. A refusal is a closed code,
  * never a provider message, and an implementation must never include the key in an exception
  * message, toString or log line.
  */
trait ProviderClients {
  def anthropic(apiKey: Secret, runtime: RuntimeConfig): Either[String, LlmClient]
  def voyage(
      apiKey: Secret,
      model: EmbeddingModel,
      purpose: EmbeddingPurpose
  ): Either[String, EmbeddingClient]
}

/** Voyage distinguishes the text being stored from the text being searched with. */
enum EmbeddingPurpose {
  case Document, Query
}

/** Builds the rag-owned Anthropic and Voyage clients. Construction makes no network call. One
  * instance serves one process, so every Voyage client it builds shares one spend counter and the
  * USD 0.30 cap is applied once. The key reaches the rag factory as an argument and is never kept,
  * logged or put in a result here. The Bedrock thunk is never used on these paths.
  */
final class RagProviderClients(
    val counter: EmbeddingSpendCounter = EmbeddingPricing.newCounter(EmbeddingProvider.Voyage)
) extends ProviderClients {
  private def noBedrock: BedrockRuntimeClient =
    throw new IllegalStateException("bedrock-not-selected")
  // The configured synthesis model id is the one the client and every agent use.
  def anthropic(apiKey: Secret, runtime: RuntimeConfig): Either[String, LlmClient] =
    SynthesisClients.create(
      SynthesisProvider.Anthropic,
      SynthesisClients.runtimeConfigFor(
        SynthesisProvider.Anthropic,
        runtime,
        runtime.model.modelId
      ),
      Some(apiKey.value),
      () => noBedrock
    )
  def voyage(
      apiKey: Secret,
      model: EmbeddingModel,
      purpose: EmbeddingPurpose
  ): Either[String, EmbeddingClient] = {
    val input = purpose match {
      case EmbeddingPurpose.Document => EmbeddingInputType.Document
      case EmbeddingPurpose.Query    => EmbeddingInputType.Query
    }
    // An unsupported model or dimension is a closed code; the rag message is never forwarded.
    val voyageConfig =
      try Right(VoyageEmbeddingConfig(input, model = model))
      catch { case _: IllegalArgumentException => Left("invalid-voyage-embedding-config") }
    voyageConfig
      .flatMap(config =>
        EmbeddingClientFactory.create(
          EmbeddingProvider.Voyage,
          input,
          Some(apiKey.value),
          () => noBedrock,
          None,
          counter,
          Some(config)
        )
      )
      .flatMap(client =>
        if (client.model == model) Right(client) else Left("embedding-provider-model-mismatch")
      )
  }
}

/** Refuses by closed code without any call. Kept for tests that need an unwired provider. */
object UnwiredProviderClients extends ProviderClients {
  val unavailable = "provider-client-unavailable"
  def anthropic(apiKey: Secret, runtime: RuntimeConfig): Either[String, LlmClient] =
    Left(unavailable)
  def voyage(
      apiKey: Secret,
      model: EmbeddingModel,
      purpose: EmbeddingPurpose
  ): Either[String, EmbeddingClient] = Left(unavailable)
}

/** Real SDK composition. Credentials come from the default provider chain, which on ECS is the task
  * role. SDK-level retries are disabled because the adapters own their bounded retry policy.
  */
final class AwsSdkPortFactory(
    credentials: () => AwsCredentialsProvider = () => DefaultCredentialsProvider.builder().build(),
    graphReaders: GraphReaderProvider = StorageGraphReaderProvider,
    providers: ProviderClients = new RagProviderClients(),
    bedrockClients: (
        Region,
        AwsCredentialsProvider,
        ClientOverrideConfiguration
    ) => BedrockRuntimeClient = AwsSdkPortFactory.defaultBedrock
) extends AwsPortFactory {
  private val providerFailed = "provider-client-failed"

  /** Runs a provider constructor and converts any failure to a closed code. */
  private def external[A](make: => Either[String, A]): Either[String, A] =
    try make
    catch { case NonFatal(_) => Left(providerFailed) }
  private def missingKey(name: String): String = "missing-aws-configuration:" + name

  /** The only place a Bedrock runtime client is created, and only for a selected Bedrock provider.
    */
  private def bedrockClient(region: Region, creds: AwsCredentialsProvider): BedrockRuntimeClient =
    bedrockClients(region, creds, overrides(callTimeoutMs))
  private def embeddingClient(
      provider: EmbeddingProvider,
      key: Option[Secret],
      model: EmbeddingModel,
      purpose: EmbeddingPurpose,
      region: String,
      bedrock: => BedrockRuntimeClient
  ): Either[String, (EmbeddingClient, Seq[AnyRef])] = provider match {
    case EmbeddingProvider.Voyage =>
      key
        .toRight(missingKey("SCHOLARCHAIN_VOYAGE_API_KEY"))
        .flatMap(k => external(providers.voyage(k, model, purpose)))
        .map(c => (c, Seq[AnyRef](c)))
    case EmbeddingProvider.Bedrock =>
      val client = bedrock
      Right(
        (new BedrockEmbeddingClient(client, BedrockEmbeddingConfig(model, region)), Seq(client))
      )
  }
  private def quietly(items: Seq[AnyRef]): Unit = items.foreach {
    case c: AutoCloseable =>
      try c.close()
      catch { case NonFatal(_) => () }
    case _ => ()
  }
  private def overrides(timeoutMs: Long): ClientOverrideConfiguration =
    ClientOverrideConfiguration
      .builder()
      .retryStrategy(AwsRetryStrategy.doNotRetry())
      .apiCallTimeout(Duration.ofMillis(timeoutMs))
      .build()
  private val callTimeoutMs = 30000L
  private def storeConfig(
      bucket: String,
      common: AwsCommon,
      ttl: Option[Long] = None
  ): StoreConfig = StoreConfig(
    bucket,
    common.tables,
    retry = RetryConfig(maxAttempts = 3),
    disposableSessionTtlSeconds = ttl
  )

  def graph(config: GraphRoleConfig): Either[String, GraphPorts] = {
    val creds = credentials()
    val region = Region.of(config.region)
    val dynamo = DynamoDbClient
      .builder()
      .region(region)
      .credentialsProvider(creds)
      .overrideConfiguration(overrides(callTimeoutMs))
      .build()
    graphReaders.open(config.neptuneEndpoint, config.region, creds, config.neptuneTimeoutMs) match {
      case Left(code) => quietly(Seq(dynamo, creds)); Left(code)
      case Right(opened) =>
        val metrics =
          new DynamoResearcherMetricStore(dynamo, storeConfig(config.graphBucket, config.common))
        Right(
          new GraphPorts(
            opened.reader,
            metrics,
            () => { opened.close(); quietly(Seq(dynamo, creds)) }
          )
        )
    }
  }

  def semantic(config: SemanticRoleConfig): Either[String, SemanticPorts] = {
    val creds = credentials()
    val region = Region.of(config.region)
    // Resolved before any other client so a refusal leaves nothing to release. A Bedrock client
    // exists only when Bedrock is the selected embedding provider.
    embeddingClient(
      config.embeddingProvider,
      config.voyageApiKey,
      config.embedding,
      EmbeddingPurpose.Query,
      config.region,
      bedrockClient(region, creds)
    ) match {
      case Left(code) => quietly(Seq(creds)); Left(code)
      case Right((embedder, owned)) =>
        val s3 = S3Client
          .builder()
          .region(region)
          .credentialsProvider(creds)
          .overrideConfiguration(overrides(callTimeoutMs))
          .build()
        val dynamo = DynamoDbClient
          .builder()
          .region(region)
          .credentialsProvider(creds)
          .overrideConfiguration(overrides(callTimeoutMs))
          .build()
        val vectorClient = S3VectorsClient
          .builder()
          .region(region)
          .credentialsProvider(creds)
          .overrideConfiguration(overrides(callTimeoutMs))
          .build()
        val storage = storeConfig(config.ragBucket, config.common)
        val vectors = new S3VectorStore(
          vectorClient,
          new DynamoArtifactRegistry(dynamo, storage),
          VectorAdapterConfig(
            config.vectorBucket,
            config.embedding.dimension,
            config.metric,
            maxTopK = 50,
            retry = RetryConfig(maxAttempts = 2)
          ),
          new S3ObjectStore(s3, storage)
        )
        Right(
          new SemanticPorts(
            embedder,
            vectors,
            () => quietly(owned ++ Seq(vectorClient, dynamo, s3, creds))
          )
        )
    }
  }

  def query(config: QueryRoleConfig, runtime: RuntimeConfig): Either[String, QueryPorts] = {
    val creds = credentials()
    val region = Region.of(config.region)
    // The model client is resolved before the storage clients so a refusal leaves nothing open.
    // A Bedrock client exists only when Bedrock is the selected synthesis provider.
    val model: Either[String, (LlmClient, Seq[AnyRef])] = config.synthesisProvider match {
      case SynthesisProvider.Anthropic =>
        config.anthropicApiKey
          .toRight(missingKey("SCHOLARCHAIN_ANTHROPIC_API_KEY"))
          .flatMap(k => external(providers.anthropic(k, runtime)))
          .map(c => (c, Seq[AnyRef](c)))
      case SynthesisProvider.Bedrock =>
        val client = bedrockClient(region, creds)
        Right((new BedrockConverseLlmClient(client, runtime), Seq[AnyRef](client)))
    }
    model match {
      case Left(code)          => quietly(Seq(creds)); Left(code)
      case Right((llm, owned)) => queryPorts(config, creds, region, llm, owned)
    }
  }

  private def queryPorts(
      config: QueryRoleConfig,
      creds: AwsCredentialsProvider,
      region: Region,
      llm: LlmClient,
      owned: Seq[AnyRef]
  ): Either[String, QueryPorts] = {
    val s3 = S3Client
      .builder()
      .region(region)
      .credentialsProvider(creds)
      .overrideConfiguration(overrides(callTimeoutMs))
      .build()
    val dynamo = DynamoDbClient
      .builder()
      .region(region)
      .credentialsProvider(creds)
      .overrideConfiguration(overrides(callTimeoutMs))
      .build()
    val storage = storeConfig(config.ragBucket, config.common, config.sessionTtlSeconds)
    // Audit pointers share the session table but must never expire.
    val permanent = storeConfig(config.ragBucket, config.common)
    val objects = new S3ObjectStore(s3, storage)
    val evidence = new IndexedEvidenceBundleStore(
      new DynamoEvidenceBundleStore(dynamo, storage, objects),
      objects,
      config.evidenceIndexPrefix
    )
    val audits = new ObjectStoreRuntimeAuditStore(
      objects,
      new DynamoQuerySessionStore(dynamo, permanent),
      RuntimeAuditStoreConfig(config.auditPrefix)
    )
    val artifacts: RuntimeArtifactStore = config.artifact match {
      case None => UnconfiguredRuntimeArtifacts
      case Some(p) =>
        val artifactObjects = config.artifactBucket
          .filter(_ != config.ragBucket)
          .map(b => new S3ObjectStore(s3, storeConfig(b, config.common)))
          .getOrElse(objects)
        new ObjectStoreRuntimeArtifactStore(
          artifactObjects,
          RuntimeArtifactPointer(p.key, p.sha256, p.sourceRunId)
        )
    }
    Right(
      new QueryPorts(
        new DynamoQuerySessionStore(dynamo, storage),
        evidence,
        audits,
        new DynamoEntityLinkCache(dynamo, storage),
        new DynamoResearcherMetricStore(dynamo, storage),
        objects,
        artifacts,
        llm,
        () => quietly(owned ++ Seq(dynamo, s3, creds))
      )
    )
  }

  def worker(config: WorkerRoleConfig): Either[String, WorkerPorts] = {
    val creds = credentials()
    val region = Region.of(config.region)
    embeddingClient(
      config.embeddingProvider,
      config.voyageApiKey,
      config.embedding,
      EmbeddingPurpose.Document,
      config.region,
      bedrockClient(region, creds)
    ) match {
      case Left(code)               => quietly(Seq(creds)); Left(code)
      case Right((embedder, owned)) => workerPorts(config, creds, region, embedder, owned)
    }
  }

  private def workerPorts(
      config: WorkerRoleConfig,
      creds: AwsCredentialsProvider,
      region: Region,
      embedder: EmbeddingClient,
      owned: Seq[AnyRef]
  ): Either[String, WorkerPorts] = {
    val s3 = S3Client
      .builder()
      .region(region)
      .credentialsProvider(creds)
      .overrideConfiguration(overrides(callTimeoutMs))
      .build()
    val dynamo = DynamoDbClient
      .builder()
      .region(region)
      .credentialsProvider(creds)
      .overrideConfiguration(overrides(callTimeoutMs))
      .build()
    val vectorClient = S3VectorsClient
      .builder()
      .region(region)
      .credentialsProvider(creds)
      .overrideConfiguration(overrides(callTimeoutMs))
      .build()
    val sqs = SqsClient
      .builder()
      .region(region)
      .credentialsProvider(creds)
      .overrideConfiguration(overrides(callTimeoutMs))
      .build()
    val storage = storeConfig(config.ragBucket, config.common)
    val objects = new S3ObjectStore(s3, storage)
    val registry = new DynamoArtifactRegistry(dynamo, storage)
    val queueConfig = (url: String) =>
      EmbeddingQueueConfig(
        url,
        visibilityTimeoutSeconds = config.queue.visibilitySeconds,
        waitTimeSeconds = config.queue.waitSeconds,
        requestTimeoutMillis = callTimeoutMs
      )
    Right(
      new WorkerPorts(
        new SqsEmbeddingWorkQueue(sqs, queueConfig(config.queue.queueUrl)),
        new SqsEmbeddingWorkQueue(sqs, queueConfig(config.queue.dlqUrl)),
        new DynamoQuerySessionStore(dynamo, storage),
        objects,
        new S3VectorStore(
          vectorClient,
          registry,
          VectorAdapterConfig(
            config.vectorBucket,
            config.embedding.dimension,
            config.metric,
            retry = RetryConfig(maxAttempts = 2)
          ),
          objects
        ),
        registry,
        new DynamoRunLedger(dynamo, storage),
        embedder,
        () => quietly(owned ++ Seq(sqs, vectorClient, dynamo, s3, creds))
      )
    )
  }
}

object AwsSdkPortFactory {
  val defaultBedrock
      : (Region, AwsCredentialsProvider, ClientOverrideConfiguration) => BedrockRuntimeClient =
    (region, creds, overrideConfig) =>
      BedrockRuntimeClient
        .builder()
        .region(region)
        .credentialsProvider(creds)
        .overrideConfiguration(overrideConfig)
        .build()
}

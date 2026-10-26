# 8A accepted decisions and limits

User accepted all recommended defaults and selected the region nearest Chicago. Use us-east-2; amazon.titan-embed-text-v2:0 is a configuration value, 256/cosine provisional until live index provisioning. No account exists; cloud access is not a local prerequisite. Region support verified from official AWS docs in this session.

Official references:
- https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-titan-text-embeddings-v2.html (Ohio in-region availability)
- https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html (256/512/1024 dimensions; 8192 tokens and 50000 characters)
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-regions-quotas.html (Ohio S3 Vectors availability)

No fake embedding quality claim establishes real Titan retrieval quality. Actual selected corpus count and real costs are unverified. Future infrastructure must retain Phase 7 runId/textHash filterability prerequisite.

Additional implementation-time sources checked (aws-knowledge MCP unavailable; official web fallback):
- Course https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-8-create-embeddings-and-populate-s3-vectors and #s3-vectors-design: separate storage/rag orders, five indexes, compact provenance, exact metrics remain deterministic.
- https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-titan-embed-text.html (Titan V2 InvokeModel JSON)
- https://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_SendMessageBatch.html (bounded queue batching and per-item response)
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-limitations.html (dimensions and metadata/request bounds)

No live API calls, credentials, resources or paid inference are required or authorized.

- https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-indexes.html: name/dimension/metric/nonfilterable metadata keys immutable after creation; future Terraform gate must decide them.
- SendMessageBatch docs additionally verified1MiB aggregate and per-message payload; enforce preflight bounds, standard queue only for8A.

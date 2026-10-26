# Read-only reference checks

Read original phase plan and required local authority. Checked course Phase8 section on2026-10-24: https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-8-create-embeddings-and-populate-s3-vectors . Separate storage/RAG work orders, fiveindexes, compact pointer metadata, provider version and exact graph/metric boundary remain binding. Local8B does not satisfy live8C gate.

Current primary AWS references read2026-10-24:
- https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html : TitanV2 supports configured256/512/1024dimensions,8192tokens/50000characters.
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-limitations.html : totalmetadata40KB/filterable2KB; max500vectors perPutVectors,20MiBrequest.

These are documentation reads, not AWS/provider SDK calls. Prior provisional256/cosine/us-east-2 decisions persist; deployment/index-immutability verification remains prerequisite before actual8C. No provider compatibility, quality or throughput claim.

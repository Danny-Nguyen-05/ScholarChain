# 7A documentation verification

Checked 2026-10-22 using official web documentation. The plan refers to aws-knowledge MCP, but no such tool is available in this session; web fallback is read-only.

- https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load-tutorial-format.html — property graph formats are Gremlin CSV and openCypher CSV; RDF formats also exist. Parquet is absent from the supported list and requires conversion.
- https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load-tutorial-format-opencypher.html — UTF-8 RFC4180 CSV; separate node/relationship files; stable :ID and endpoint columns; optional numeric properties can be blank. The approved scoped Spark export is therefore required, with no live load in 7A.
- https://docs.aws.amazon.com/neptune/latest/userguide/data-api-dp-loader.html — StartLoaderJob accepts csv/opencypher and RDF formats, not Parquet; real loader adapter remains 7B.
- https://docs.aws.amazon.com/neptune/latest/userguide/data-api.html — neptunedata exposes bulk-loader and query APIs.
- https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-7-implement-storage-adapters-and-loading — course source consulted; plan is the bounded 7A work order. Required technology stack, Configuration and S3 Vectors design consulted. AWS execution stays a later human-gated activity.

No runtime compatibility or live loading is claimed from documentation.

Additional current references (7A contracts/fakes; real graph/vector adapters remain 7B):

- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html — conditional PutItem prevents replacing an existing composite-key item; ordinary put otherwise overwrites.
- https://docs.aws.amazon.com/neptune/latest/userguide/opencypher-parameterized-queries.html — queries accept a separate parameter map; no user-text concatenation needed.
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-limitations.html — dimensions 1–4096; PutVectors 500 vectors/call; GetVectors 100; metadata 40 KB total, 50 keys, filterable 2 KB, 10 nonfilterable keys; payload 20 MiB. Current page lists top-K 10,000 and query response pages of 100. Service capabilities/SDK constraints must be reconciled by the 7B adapter; these are documentation limits, not live verification.

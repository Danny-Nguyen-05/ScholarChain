# Read-only official documentation checks

Consulted 2026-10-22 America/Chicago. No AWS knowledge MCP is exposed in this session; official AWS pages accessed via web fallback, without account/provider calls.

- [Course Phase 7](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-7-implement-storage-adapters-and-loading)
- [Neptune loader APIs](https://docs.aws.amazon.com/neptune/latest/userguide/data-api-dp-loader.html)
- [Neptune openCypher CSV](https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load-tutorial-format-opencypher.html)
- [Parameterized queries](https://docs.aws.amazon.com/neptune/latest/userguide/opencypher-parameterized-queries.html)
- [S3 Vectors limits](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-limitations.html)
- [S3 Vectors Query API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_S3VectorBuckets_QueryVectors.html)
- [DynamoDB transaction token](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactWriteItems.html)

Observed points: openCypher CSV accepts explicit relationship IDs and requires UTF-8/RFC4180. Neptune loader exposes AUTO resume mode and configurable role/region. The current vector limitations page lists dimensions 1–4096, total metadata 40 KB, 50 keys, filterable metadata 2 KB, 10 nonfilterable keys, request payload 20 MiB, PutVectors 500 and GetVectors 100, top-K 10000 but 100 results per page. QueryVectors now has nextToken/queryMode; pinned SDK compatibility must be reconciled explicitly. DynamoDB ClientRequestToken is at most 36 characters and valid for 10 minutes; use the same token/request within each bounded logical retry. Implementation-specific conclusions and citations belong to the storage README.

## Community projection dependency

The existing CSV has no community membership properties/edges. Storage-owned loader enrichment from validated `metrics/type=communities` is within the plan’s selected runtime lookup properties, preserving existing node/edge IDs and source convergence qualifications. Dynamic property access is explicitly unsupported by [Neptune openCypher compliance](https://docs.aws.amazon.com/neptune/latest/userguide/feature-opencypher-compliance.html); use static property names and parameterized lookup values. This is a design decision, not live-service validation.

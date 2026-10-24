# Official documentation checks — 2026-10-23

Read-only web fallback used; no AWS account/API calls.

- https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-limitations.html — current service batch, metadata and query limits checked; adapter README holds the detailed values/citations.
- https://docs.aws.amazon.com/neptune/latest/userguide/load-api-reference-load.html — existing loader behavior, source prefixes and data-only bulk load.
- https://aws.amazon.com/neptune/pricing/ — provisioning/runtime choices affect cost; regional calculator validation remains required for Phase14C.
- https://aws.amazon.com/s3/pricing/ — storage, requests, retrieval and transfer can contribute to charges.

The user selected5USD as an incremental test budget, excluding already-provisioned infrastructure. This is not an observed bill, verified region-specific estimate or automatic billing ceiling. No current cost or cloud execution is claimed. Phase14C must validate concrete configuration, prices, cleanup and human budget approval before running.

- https://aws.amazon.com/dynamodb/pricing/ — read-only pricing model reference checked2026-10-23; no concrete regional quote or cost calculation claimed.

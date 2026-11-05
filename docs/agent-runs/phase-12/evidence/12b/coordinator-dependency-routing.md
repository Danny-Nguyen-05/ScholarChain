# 12B implementation dependency routing

Owner: coordinator; recipient: infra-engineer `/root/infra_12b`. This is implementation coordination, not an independent review or approval.

- Current ServiceMains accepts only `unconfigured` and `offline-synthetic`. Keep service activation disabled and disclose the missing live composition. Environment-variable/resource wiring alone is not proof of readiness.
- Queue backlog/task metric math needs Container Insights `RunningTaskCount`. Author the metric source together with the scaling policy.
- EMR service role was trust-only in 12A. Provide documented scoped control-plane permissions, or refuse activation until concrete required permissions are supplied; do not claim working EMR merely from a mock plan.
- New Step Functions CMK encryption requires execution-role GenerateDataKey/Decrypt on the project key with the exact state-machine encryption context. A queue-only ViaService condition does not authorize workflow payload encryption. Routed before final validation; owner asked to add a distinct scoped statement and feature assertion. Primary source is in coordinator-documentation-sources.json.

Any remaining live permission effectiveness, quotas, runtime compatibility, pricing and readiness checks belong to their later explicit gates.

- DynamoDB native ThrottledRequests requires TableName and Operation dimensions; prefer table-level ReadThrottleEvents/WriteThrottleEvents or supply the operation dimension. Routed before freeze with official metrics-dimensions URL.
- S3 Vectors indexes must also declare non-filterable metadata key textS3Uri. Existing VectorAdapterConfig and both live ingest/query preflights require exact metadata-set equality, not just dimension/metric. Routed to infra-engineer with source lines and requested resource assertion before final freeze.

- Graph autoscaling introduces multiple replicas. Existing service README160–161 and ServiceMains23–24 require a stable cursor signing secret across replicas; otherwise a random per-process key invalidates pagination across tasks. Routed a graph-service cursor-key ARN activation prerequisite, synthetic fixture update, feature test and documentation before freeze. Secret values are never read.

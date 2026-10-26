# Repair-round live packet — authored, never executed

Only local render-only and offline tests are permitted in this repair. All command lines below are authored examples; only test code invokes render-only execution against temporary fixtures. Neither live entry point is executed. No AWS account, credentials, deployment or live approval exists. All templates are disabled examples: zero caps, executionApproved=false, expired timestamp, unresolved names and unvalidated prices. They are not human decisions or approvals.

## Produce a real-model manifest locally

The render command does not embed, construct an embedder/client, create fake state or write vectors. The rendering configuration shares the explicit selection/template/model/pointer fields with LocalEmbeddingConfig; its use here does not imply fake vectors under the real model. Fill the model ID/version/dimension, ordinary text bucket/prefix, source/manifest bounds and rendering limits in a new reviewed configuration. The zero selection limits in the template intentionally require operator decisions. Preserve exact source qualifications and abstract permission/fallback semantics.

Authored command:
```sh
sbt -batch 'rag / Compile / runMain edu.uic.cs441.scholarchain.rag.EmbeddingManifestMain --export /absolute/path/to/completed-phase6-export --work-manifest /absolute/path/to/completed-phase6-export/load-manifests/s3vectors.json --config /absolute/path/to/reviewed-render-config.json --manifest-output /absolute/path/to/real-model-manifest.json --report /absolute/path/to/render-report.json'
```

The future ingest approval must bind the resulting exact manifest bytes and live configuration bytes. Model ID, version, dimension and pointer settings must match. Rendering for a real model is local authoring, never authorization to embed.

## Future 8C ingest — UNEXECUTED

Use the existing LiveEmbeddingIngestMain command with --config, --manifest, --approval, --report and --run-id. Approval operation must be ingest. It must bind exact config, manifest and Phase14 gate hashes; environment/run/expiry and all vector/concurrency/embedding/dollar caps; explicit human execution/pricing/budget validation. It checks existing indexes instead of provisioning them. The report now includes model ID/version/dimension, per-index written counts, rejected reasons and rejected-report URI in addition to existing counters/runtime/assumed bounds. No actual report or service compatibility is claimed here.

## Future 8C query and latency smoke — UNEXECUTED

Populate the query-smoke configuration with the same approved real model, deployed text/vector buckets and five indexes. Choose at least five reviewed queries covering every index and actual expected vector keys from the reviewed real-model manifest. Expected keys are source-backed test choices, not invented researcher identities or proof of graph metrics. Choose topK, samples per query and explicit request, embedding-attempt, object-read, object-byte and price caps. Fifty query samples per index is a future workload choice, never an observed result in this repair.

Human writes a separate approval with operation=query-smoke, exact smoke configuration/manifest/Phase14 gate hashes and explicit queryRequestCap, queryEmbeddingCallCap and queryObjectReadCap. An ingest approval cannot authorize querying, or vice versa. Price assumptions must cover query embeddings including retries, vector requests, object reads and the approved retention/overhead window; estimated bounds are not billing guarantees. The configured fixed overhead must also cover the five existing-index GetIndex checks and any credential/network/ancillary request charges in the approved window. The query composition makes no DynamoDB calls.

Authored command (DO NOT RUN during this repair):
```sh
sbt -batch 'rag / Compile / runMain edu.uic.cs441.scholarchain.rag.LiveEmbeddingSmokeMain --config /absolute/path/to/human-smoke-config.json --manifest /absolute/path/to/reviewed-real-model-manifest.json --approval /absolute/path/to/human-query-smoke-approval.json --report /absolute/path/to/live-query-smoke-report.json --run-id approved-query-smoke-run'
```

The smoke configuration retains the full shared LiveEmbeddingConfig and its conservative common manifest/resource/cost validation; those nested limits must remain consistent with the reviewed manifest as well as the stricter query-specific caps. It can refuse a query workload conservatively rather than widening an approval. The query smoke command is read-only against provisioned data after its approval gate: configured model embeds query text, configured existing indexes return neighbors, and each hit resolves through the approved ordinary-S3 bucket/prefix with hash/byte checks. It reports expected-neighbor outcomes, request/sample counts and per-index latency p50/p95. Offline tests exercise only pure planning/report helpers and refusal before client construction. No live smoke invocation or approved execution route is run in 8B.

Every sbt command uses the exact JDK17/PATH/SBT_OPTS environment recorded in commands.md. Phase14 Terraform deployment and separate human approvals remain prerequisites for either future live command.

## Cleanup — future human gate

No deletion or infrastructure cleanup is executed or authorized by these templates. Retain reports, manifests, rejected records and ledger evidence, identify exact objects/vectors/bindings actually owned by an approved run, and obtain separate human approval for a bounded deletion inventory. Shared and unchanged data is not owned merely because it appeared in a manifest. Route infrastructure changes through reviewed Terraform and approved deployment execution. Avoid partial deletion of immutable bindings/namespaces; verify final counts and record any retained resources. The query command itself writes only its local report and requires no cloud data cleanup.

N10–N14, N2–N8 and R2–R3 remain deferred. Actual live quality, corpus count, latency, cost and cleanup remain unverified. The new template values intentionally are not executable approval inputs.

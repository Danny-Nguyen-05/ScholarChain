# Subphase 12B — Step 0 answers

Coordinator record of conversation instructions; this is not a human-owned cloud approval or spending gate.

User start instruction, verbatim: `alright let do phase 12b`

User answer to the complete recommended setup below, verbatim: `use all recommendations`

Approved local-authoring scope: only 12B, beginning from committed and pushed 12A plus repair/review records on branch `phase-12`, HEAD `a83f62e9af56058a170075f98c4e027d039567ec`. Prior user instruction to commit/push was fulfilled for 12A and is not reused as authorization to commit 12B. The user independently supplied the APPROVE review retained in `../../review.md`; no reviewer is launched by the coordinator.

## Accepted recommendations

1. Account/profile/region remain pending. Environment remains `course`. Account reminder due before 12C or an earlier separately approved 12D.
2. Budget remains pending until 12C; no spending authorized.
3. Neptune Serverless, minimum 1 NCU, maximum 2.5 NCUs; encrypted, private, IAM authenticated, seven-day backups and deletion protection except explicit cleanup mode. Engine/version and regional availability require later validation. Ohio is a pricing example only, not a selected region.
4. Continue offline by authoring a disabled EMR module with explicit release/runtime inputs and unverified compatibility. Bounded one primary, one core, at most two task nodes, no Spot. The plan prefers a live 12D spike before final authoring; the selected offline alternative does not establish Spark/Scala compatibility or approve a spike. No compatible runtime is invented.
5. Permit `s3:DeleteObject` only on configured EMR output prefixes, with written commit/temporary-file rationale and versioned delete-marker behavior. Preserve no DynamoDB actions in EMR data role.
6. Separate pipeline/loader producer identity with queue-only send permissions and required KMS access. Actual production enqueue caller deferred to Phase 13; no caller is invented.
7. ALB access logs off and documented for this course stack; no separate SSE-S3 access-log bucket. Existing SSE-KMS logs bucket is not a supported ALB access-log destination.
8. Certificate remains pending; public ingress CIDRs empty. HTTPS listener disabled until configured. No HTTP listener.
9. Runtime activation initially disabled. Configurable activated task defaults: 0.5 vCPU / 1 GiB each; query-api, graph-service and semantic-service each minimum 1 / maximum 2; embedding-worker minimum 1 / maximum 4. HTTP service CPU target 60%; worker queue backlog target 10 messages per task. Bounds are authoring defaults, not measured load-test sizing or a budget fit claim. Disabled runtime cannot activate via autoscaling.
10. Exactly five float32 S3 Vector indexes, dimension 256, cosine: `researcher-profile-v1`, `collaboration-community-v1`, `paper-abstract-v1`, `collaboration-path-v1`, `topic-institution-summary-v1`. Names: `modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/Phase7Configs.scala:86-92`; dimension/metric/planned embedding model: `modules/rag/README.md:57-61`. Use native pinned AWS provider resources.
11. Configurable model IDs with narrowly scoped InvokeModel grants. Retain planned Titan V2 embeddings (`amazon.titan-embed-text-v2:0`); synthesis model unset with no grant for an unset model. No live model access or invocation verified.
12. Seven-day logs; Phase 15 dashboard for API latency/errors, ECS, queue, EMR, Neptune, DynamoDB, vector-client and LLM usage. Configurable alarms: HTTP errors above 5%, API/graph p95 above 5 seconds, oldest queue message above 5 minutes. Notification target unset; no invented email. Published application/collector integration remains a deployment dependency where not currently implemented.
13. Add a minimal functional Step Functions state machine and least-privilege role to address the explicit course requirement. This supersedes the earlier local-plan omission; no instructor approval or waiver is claimed.
14. Additional recommendation accepted: runtime activation stays disabled because current service entrypoints lack live AWS adapter composition. Record the Phase 13/14 deployment dependency without editing application code in 12B or claiming live readiness.

No additional questions are pending. All numerical defaults remain configurable with finite validation bounds. Preserve 12A invariants, route resources only in `modules/network`, and exact Terraform 1.13.5 / AWS provider 6.44.0 pins. Omit OpenSearch, EventBridge and Glue unless an implemented use requires them; operational scripts remain Phase 13. Do not edit human-owned decision/approval/commit files.

## Documentation consulted for sizing

- AWS Ohio public price list: https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonNeptune/current/us-east-2/index.json (publication date 2026-09-11T12:44:56Z; consulted during Step 0). Standard `db.t4g.medium`: USD 0.093/hour; standard Serverless: USD 0.1608/NCU-hour. At 1–2.5 NCUs, compute alone is USD 0.1608–0.402/hour per instance. Storage, I/O, backup, network and other stack charges are additional. These figures do not establish budget fit, free-tier eligibility, measured cost, regional choice or deployment authorization.
- AWS capacity limits (minimum can be 1; smallest maximum is 2.5): https://docs.aws.amazon.com/neptune/latest/userguide/neptune-serverless-capacity-scaling.html
- AWS small-T development/performance limitations and openCypher caveat: https://docs.aws.amazon.com/prescriptive-guidance/latest/neptune-well-architected-framework/cost-optimization-pillar.html
- AWS instance guidance: https://docs.aws.amazon.com/neptune/latest/userguide/instance-types.html
- Provider 6.44.0 Neptune cluster / instance: https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/neptune_cluster and https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/neptune_cluster_instance
- Provider 6.44.0 native S3 Vector index: https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/s3vectors_index

Public documentation/pricing fetches are not account API access. No AWS credential discovery, real plan, apply/destroy/import or paid model call is authorized by this answer.

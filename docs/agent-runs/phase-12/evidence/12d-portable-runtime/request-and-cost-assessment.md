# Artifact inventory does not establish a whole-attempt request cap

The offline packaging task now measures the candidate JVM runtime including the immutable job at321876762bytes, optional separate YARN JAR archive at310978586bytes, and85-file G1 input archive at66755bytes. The job is already inside the runtime archive and is not counted again. Full expanded contents, hashes, modes, provenance and local verification are retained by the build owner. These are local files, not S3 objects that have been created or a selected cloud staging strategy. Java17 remains an external platform prerequisite; no compiler/REPL or whole-OS image is bundled.

`staging-object-inputs.json` distinguishes three measured candidate files from five unimplemented reservations: public metadata1MiB, bootstrap/config64KiB, protected PEMzip64KiB, result/log archive250000000bytes, and controller/control storage1MiB. Certificate keys were neither created nor read. Every reservation is hypothetical; it is not a measured output, implemented limit, credential hash or cloud object. The result/log reservation does not bound EMR’s own log-object creation.

## Conditional transfer arithmetic

The replay uses64MiB upload parts for objects larger than64MiB. A successful multipart sequence has initiation, each part and completion. It assumes one post-upload HEAD plus one streaming verification GET, then one HEAD and either a whole-object GET or64MiB ranged GETs for each listed consumer. One and three attempts per API are analysis cases, not configured retry limits. Future transfer-client behavior must match the selected case or be inventoried anew. Smaller ranges, repeated opens, multipart abort/list/reconciliation and copies need separate counts.

| Unselected staging case, including all five reservations | Objects | Bytes stored once | Upload API units, one success | Whole-object GET/HEAD | Ranged GET/HEAD |
|---|---:|---:|---:|---:|---:|
| Runtime plus G1 inputs, no separate YARN object |7|574171741|18|38|46|
| Same plus optional YARN JAR archive |8|885150327|25|44|60|

With three attempts per inventoried API, those partial counts become54upload/114whole-object-read/138ranged-read, or75/132/180 with the optional archive. These are conditional artifact-transfer subtotals only, not the complete1000PUT/LIST/10000GET/HEAD envelope. The conditional stored-once sizes are below the previously modeled1000000000bytes; that comparison does not include unlimited versions, additional logs or orphaned multipart parts. Three whole-object copies of everything would instead be1722515223 or2655450981bytes, exceeding that storage assumption. That is a separate stress case, not a claim that three per-API retries necessarily create three completed versions.

## Missing bounds and cost decision

There is no implemented transfer/controller/cloud-root here, so full-attempt PUT/LIST, GET/HEAD and KMS maxima remain null. Requests still depend on EMR/bootstrap/repository access, service logging/rotation, leases/heartbeats, guard/cleanup state changes, failure paths, retry/pagination/range settings, multipart ambiguity, encryption operations, certificate delivery and the selected HDFS/YARN staging route. Spark’s YARN source describes a fallback JAR-archive upload if neither yarn.archive nor yarn.jars is supplied; the future root must explicitly inventory where it goes. Do not silently count a second S3 archive as free or assume a two-node job always downloads each object exactly once.

AWS documents both GenerateDataKey and Decrypt permissions for SSE-KMS multipart uploads. This does not prove a universal one-operation-per-request KMS ceiling. Preserve the previous model’s conservative proxy as a modeling assumption only; do not use this inventory to certify31000KMS requests, claim bucket-key/caching savings, or hide uncounted operations. Project-bucket requests and provider-owned repository requests must be classified rather than blindly charged to or excluded from the same bucket budget.

The earlier nominalUSD5.30 remains above the proposedUSD5. The earlierUSD4.82 lower-request alternative remains unselected and unproven. No price, budget, region, instance type/count, attempt allowance, retention or lifetime is changed by this step. Actual local packaging tests cannot establish F4/current funds, AWS IAM effectiveness, EFS metering, service behavior or a live cost cap.

## Next bounded task after independent review

A separate offline infra-owner implementation can turn these hypotheses into explicit artifact/control/log layouts, bounded request/retry/byte policies, protected prearmed lease/unknown-ID handling and failure tests. Carry implementation-constraints.md: no extra cluster canary, no paid certificate service, explicit volume count and honest live residual-risk gates. Current work does not implement that root. It needs its own work order and independent review before any account preflight or real plan. No cluster, security mutation, spending or cleanup is authorized by this assessment.

## Observed local logging volume

The completed local[2] pipeline emitted a184489197byte Spark event log. Its exact bytes are preserved separately as an11283159byte gzip, and239 product-export files are preserved in a185284byte tar.gz. The event log was excluded only from the product archive and retained independently, with decompressed-byte SHA verification. This local observation is not an AWS CloudWatch billing measurement and does not cover all EMR/bootstrap/guard logs. It provides no proof that the proposed0.25GB ingest/retention assumptions are sufficient; preserve that remaining uncertainty rather than substituting the small compressed size for billed ingest.

## Runtime security finding

Ordinary relocation, separate-JVM sentinel and local[2] full28-table comparison passed. Both required-authEngineVersion2/AES-GCM/noSASLfallback/spill-encryption probes exited2 after successful initial authentication but unanswered worker/client registration. Neither produced an executor-task success receipt. Root cause is unknown; no application, cipher or version was changed. This is an additional unresolved launch-readiness condition, so a bounded offline security/runtime investigation precedes any assertion that this bundle is suitable for the secure EMR design. No cached Linux test could be attempted through the expected Docker socket because it was absent; no daemon/image installation/start was performed.

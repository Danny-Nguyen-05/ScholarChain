STATUS: COMPLETE (F6/F9 service implementation and root-observed targeted green gates; fullcheck/Docker gates pending)
OWNER: service-engineer /root/service_engineer, native delegated agent
WORK ORDER: Subphase10B repair round1, user-authorized F6 plus F9 only. Read docs/agent-runs/phase-10/evidence/10b-repair-1/external-review.txt and inherited plan Sections6/10. Preserve authorized uncommitted10B; base/HEADc85da7365927a1f7d8ee5ab1f67c5c1a128391b3,phase-10. Exclusive edits modules/services/**. No F7/F8/F10–F15 implementation, including expressly excluded F12 broad422 code forwarding. No subagents/reviewer,cloud/provider calls,commits,pushes,human-gate edits.
FILES CREATED:
- modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/GraphRequestDeadlineSpec.scala
FILES MODIFIED (repair delta only):
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/ApiContracts.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/ApiApplication.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/DownstreamClient.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/GraphApi.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/RemoteServices.scala
- modules/services/src/main/resources/openapi/scholarchain.v1.yaml
- modules/services/README.md
COMMANDS RUN:
Read-only cat/sed/rg inspected the exact external review, current graph boundary/client/circuit implementation, ApiError and README/OpenAPI statements. No secrets or credential files read. Created module regression source first without production changes; staged narrow production patch script only at /tmp/phase10b-r1-apply-service-f6.py while root ran red gates. On explicit root release ran `python3 /tmp/phase10b-r1-apply-service-f6.py` (exit0: Applied onlyF6deadlineclassification andF9observed-countwording), then corrected the new module503 metric expectation to the pre-existing metrics contract without changing production503 metrics. No sbt/formatter/approval or background process was started by this service agent; root centrally ran exact plan JDK17 gates with pre-run source hashes.
Root-observed gate evidence:
1. /tmp/phase10b-r1-independent-red.log exit1,wall6.786s,SHA256391d4db4595f8947d2d84d3e345213188a0e9c405c61597c3dc57d1173791fab:4tests3pass1fail. Exact defect:backendcalls3!=4; old first request retried3times and opened the breaker, denying later requests. Root retained formatted red source and hashes.
2. /tmp/phase10b-r1-module-red.log exit1,wall5.142s,SHA25604eda8511d066063ed84ffd2168302cae41b3ff0d71beef014fbb1f2816a2681:5tests2pass3fail. First two failures demonstrate old graphdeadlinecode/retry behavior. Third failure was solely a new-test assumption that503 contributes to api_downstream_errors_total; existing contract counts502/504 only. The circuitOPEN assertion already passed. Corrected that test to503count0 versus502/504count1, retaining all failure-classification assertions. No production metrics expansion or weakened breaker guard.
3. Root reported targeted green exit0,wall11.909s,log SHA2563136fb0051ab6bbb472eac85bc4be4db1a5c311adadb120a9fe9888b590884c1:services31/31 in5suites,independent10A/B41/41 in7suites,packageServicespassed. Exact central command/logpath retained by root; no fabricated command reconstruction here.
4. Root fullcheck and build-owner Docker rebuild/smokes running at report checkpoint; not claimed passed. Root will provide exact final results, commands, elapsed and hashes.
README only updated after code/resource freeze to record observed31/41 targeted counts; no production/resource changes after targeted green.
TEST RESULTS:
New module5cases:
- Local graph operation's actual bounded expiry returns504 GRAPH_DEADLINE_EXCEEDED retryablefalse.
- Repeated valid typed graph deadline responses (threshold+1) make exactly one backend call each, preserve CLOSED graph circuit and readiness, use fixed safe message, count graph_request_deadlines_total without dependency errors, and allow later normal success.
- Retryable/wrong-status/malformed/missing-fields/wrong-operation/wrong-dependency/unrecognized-code deadline markers still count as dependency failures and open the circuit; arbitrary downstream messages are never forwarded.
- Actual client timeout with no response remains retryable DOWNSTREAM_TIMEOUT and opens circuit.
- Actual connection refusal remains dependency502 and opens circuit.
Root targeted green services31/31,independent41/41 passed. Independent owner's4new wire cases are separately authoritative for full public caller-trace/readiness/backend-count acceptance. Existing F1–F5 and prior10A/10B regression suites passed in root targeted gate. Fullcheck/Docker pending at assembly.
VALIDATION RESULTS:
F6 introduces one closed safe ApiError.graphDeadline marker:status504,error GRAPH_DEADLINE_EXCEEDED,retryablefalse. GraphApi's local interruptible operation boundary converts only its own execution-budget timeout to that marker; transport timeout in RemoteService/DownstreamClient remains distinct retryable DOWNSTREAM_TIMEOUT.
RemoteService byte-bounds every error body before classification. It accepts the marker only for dependencyNamegraph,GET,allowlisted internal graph node/neighbors/metrics/paths operation,status504,and an exact four-field typed error object whose code matches, retryable isfalse, message isstring and trace isbounded safe correlation token. It discards downstream message/trace and emits a fixed safe message; public ApiApplication supplies callertrace. Every other status/body preserves the existing status mapper. In particular422 behavior is unchanged (F12 out of scope).
DownstreamClient recognizes only the exact closed status/code/nonretryable marker as request-specific:one attempt,no breaker failure,server reachability succeeds. All other502/503/504 retain existing retry/failure policy, including nonretryable unknown5xx, malformed markers, readiness errors and real transport failures. Recognized request deadlines increment a separate graph_request_deadlines_total, not dependency-error/transport-timeout counters; ordinary HTTP504/status/latency still describe the public outcome. No blanket nonretryable5xx exemption added.
F9 README now accurately distinguishes prior targeted3 independent36/36sixsuites, final10B17/17foursuites,and37combined only inside fullcheck625. Root owns corresponding repairs.md correction. Added separate observed repair31/41 targeted checkpoint.
OpenAPI/README document the safe deadline code and request/dependency classification. Production/resource source frozen after root green.
ASSUMPTIONS:
Only F6 and F9 authorized. Distinct graph marker is trusted only after bounded typed whitelist parsing and appropriate graph operation/dependency matching; generic retryablefalse alone never waives breaker failures. Current numeric dependency metrics retain prior503 omission, explicitly tested rather than expanded in this repair.
RISKS:
- User-designated nonblocking F7,F8,F10–F15 remain untouched; F12 specific422 graph codes still map to existing UNSUPPORTED_QUERY through proxy.
- All prior disclosed live adapter/deployment, durable query dispatcher, PROCESSING recovery, snapshot/cursor and raw SQS redrive limitations remain unchanged.
- No live AWS/provider calls or production traffic used; local HTTP fixtures exercise real transport behavior. Native tests/containers may produce synthetic fixture identifiers only.
- New code/package changes require rebuilt image evidence; build-owner is doing so. Old images are not asserted current for this repair.
MANUAL ACTION REQUIRED: Root completes full JDK17 check and rebuilt four images/three-main remote smoke/outage checks, assembles evidence and recheck reviewer prompt. User launches read-only independent recheck and owns acceptance/commit/human gate. No human records authored here.
BLOCKED-ON OWNER: None for service repair implementation; root/build final evidence pending.
BLOCKED-ON EVIDENCE: Targeted31module/41independent/package green observed; fullcheck and rebuilt Docker results pending at report checkpoint.
NEXT GATE: Root final fullcheck + rebuilt images/outage smoke, then user-launched F6/F9 read-only recheck. Stop without additional findings or next phase.

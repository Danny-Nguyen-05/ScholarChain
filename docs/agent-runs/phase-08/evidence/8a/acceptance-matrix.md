# 8A acceptance evidence

| Requirement | Meaningful checks | Observed affected evidence |
|---|---|---|
| Additive wire/model/key contracts | Four fixed wire snapshots, exact hello SHA, explicit collision-safe frame, model/version/dimension changes; invalid model/key/index/hash rejected | core EmbeddingContractSpec9/9; independent contract5/5 |
| Five deterministic templates/provenance | Exact supplied fields/numbers and refs, reversed field order gives byte-identical text, upstream qualifications retained | RAG14/14 and independent rendering4/4 include these cases |
| Paper selection | Explicit permitted text plus permission ref; missing/blank abstract fallback; no acquisition or invented value | RAG/independent rendering suites |
| Chunking/IDs | Hand-derived whitespace/overlap, unbroken spans, Unicode, blank/count limits; identity binds window/template/policy/text | RAG/independent rendering suites |
| Versioned embedding adapter | Injected SDK request JSON/dimension/timeout, retries then success, exhausted/permanent sanitized failures, finite dimension, conservative input bounds, cross-call semaphore | RAG14/14, no live calls |
| Canonical S3 text and compact metadata | Full-provenance canonical envelope/pointer, SHA checks, no source text in compact metadata, configured identity allowlist | storage12/12; independent storage6/6 |
| Dedup/conflict/recovery | Written first-run vs unchanged replay, zero replay embedding calls; same-key changed text conflict; prepared vector after lost success/completion marker, no reembedding | storage12/12; independent storage6/6 |
| Queue adapter/fake | At-most10, configured per-message and1MiB aggregate preflight, exact SDK shapes, partial-send/malformed receive visible, visibility expiry/stale receipts/backlog | storage/independent storage suites, SDK stubs only |
| Failure/counter/log evidence | RunLedger observed retries/permanent failures, rejected JSON, fixed throughput clock, count-only structured event with payload exclusion | storage12/12; independent storage6/6 |
| Semantic boundary | Stored envelope length/hash/key/model/text match, Unicode excerpt, negative-distance ranking, descriptive label and false graph/metric authority | core/RAG/independent suites |
| 7C-L2 prerequisite | Four additional char/interpolation/helper adversarial regressions; prerequisite suite8/8 before RAG at0 roots, later8/8 at3 actual roots | prerequisite-2 and targeted-3 |

Final affected logs: targeted-2 core9/storage12; targeted-3 RAG14/independent23, exits0. Full repository gate later passed718/718, exit0; final disposition is in final-check.json and parent reports.

Not 8A scope: five-query retrieval smoke, fixture/real-slice CLI ingestion, and authored unexecuted8C command/approval packet (8B); live deployment/execution/minimum corpus/quality/cost (later approved8C). No instructor approval or cloud compatibility inferred.

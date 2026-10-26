# B1–B4 repair evidence

Local verification only; external recheck pending. Full check exit0,901passed0failed; targeted140/140.

| Finding | Source behavior | Hand-derived regression evidence |
|---|---|---|
| B1 | Independent request intent fixes metric/measure/operation, exact ordered window/comparison vectors, config defaults and explicit total-author conversion; wrong model values retry→safe fallback/Unsupported. | Runtime9ARepairSpec15explicit intent tables plus exact-window/default/conversion checks; IndependentRuntime9ARepairPlannerSpec37positive/negative cases including alternate configured measure/window defaults. |
| B2 | Group canonicalIDs before dedicated cap; bound merged provenance with original distinct totals; overflow Ambiguous contains totalCandidateCount/truncated and stable bounded list. | RuntimeContractSpec4newcompatibility/bound/disclosure tests; module and independent many-row/single-ID and5-ID/cap2cases, exact retained/count assertions. |
| B3 | Known researcher absent in a declared window returns Missingcontext and remains Resolved/Ambiguous; undeclared window rejected. | Storage context absence test; module actualartifact composition; IndependentRuntime9ARepairResolverSpec3actual-fake window/absent-homonym cases. |
| B4 | Successful load cached per immutable reader pointer; immutable keyed indexes; warm reads no GET/parse/validation; cold concurrent reads oneGET; failed loads notcached. | RuntimeArtifactStorageSpec mixed six-port warm calls with secondGETthrow, concurrent six-port cold calls GETcount1, missing/rejected/corrupt first-loadretry. First corruption is rejected. No production latency measurement claimed. |

Raw logs/result bindings: core-targeted-1.log, storage-targeted-1.log,
independent-targeted-1-result.json/excerpts, rag-format-targeted-1.log (testcompile failure),
rag-format-targeted-2.log (40passed+format), check-1-result.json/excerpts. Full raw paths and
SHA-256 are retained for larger logs. source-files.json hashes34cumulative paths;
repair-files.json gives16before/after deltas against source-before.json.

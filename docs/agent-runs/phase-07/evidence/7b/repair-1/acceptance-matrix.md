# F3/F4 acceptance evidence

All listed tests passed in the first affected invocation (storage23, independent54, CSV4; exit0). Full-gate results are recorded separately after completion. These are offline SDK stubs, not live Neptune proof.

| Check | Implementation | Module / independent evidence |
|---|---|---|
| Explicit pending/success/failure classification, including conflicts/deadlock/unknown | NeptuneJobAttempts.scala NeptuneLoadStates; NeptuneGraphLoader polling | NeptuneRepairSpec terminal-state case; IndependentStorageGraphLoaderSpec failed/conflict/deadlock/unknown cases |
| Final failure permits one new job, preserving ledger failure/retry | Immutable attempt versions and terminal markers; NEW mode on recovery | Module terminal-state case; independent LOAD_FAILED and write-conflict rerun cases with fresh adapter/shared ports |
| Timeout retains pending job with no resubmission | Timeout does not write a terminal marker | Module timeout case; independent timeout recovery case |
| Completed fingerprint remains Unchanged with no upload/submission | Completion registry checked before uploads | Module terminal recovery completion check; independent completed rerun check |
| Legacy registry history preserved without deletion | Legacy record adopted; append-only failure marker/new attempt | NeptuneRepairSpec legacy case |
| Recovery documented | modules/storage/README.md Neptune loader paragraph | Explicit mode, timeout, legacy and sanitized-failure account |
| Structural Document JSON supports every kind, exact numbers | AwsDocumentJson.value and AwsJson enum | Module nested primitive/BigDecimal/beyond2^53 case |
| Reader node preserves CRLF/tab/quote/backslash/Unicode | Structural response decode, JSON library escapes strings only when rendering | Module special-text case; IndependentStorageGraphReaderSpec structural node case, exact UTF-8 equality |
| Neighbor property preserves same text | Structural property access and lossless render | Module special-text case; independent multiline neighbor case |
| Loader status uses shared converter | NeptuneGraphLoader.status | All recovery/status cases exercise structural SDK Documents |

Repair-only paths: repair-source-changes.json. Source binding before repair: source-before.json. Exact commands and raw-log hashes: commands.md and targeted-1.json. Original F3/F4 finding text: external-review.txt.

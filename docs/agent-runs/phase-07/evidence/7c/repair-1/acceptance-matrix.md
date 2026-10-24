# 7C-M1 acceptance evidence

| Acceptance | Implementation / offline regression |
|---|---|
| Both DELETEs return count | AwsLiveGraphCleanup fixed queries RETURN count(r/n) AS deleted; SDK stub asserts query shape |
| Count equals exact owned-ID cardinality | Structural AwsDocumentJson number with longValueExact; duplicate IDs refused; zero/mismatched/nonintegral/string counts fail |
| Post-delete edge absence | Separate read-only exact-ID edge query must return empty result |
| Post-delete node absence | Production NeptuneGraphReader.node must return StorageResult.Missing, not Found/Rejected |
| No premature cleaned journal state | All-or-none graph batch; each SDK test callback asserts both memory and persisted journal remain created during deletes and point reads |
| Zero-match must not mark cleaned | First test covers edge0 and node0 after edge1; memory and persisted journal remain created |
| Correct count alone insufficient | Edge-present/nodeFound and read-exception tests keep created state |
| Success verified before marking | Last case asserts deleteedge/deletenodes/readedge/3readnodes ordering then all persisted entries cleaned |
| Live behavior remains gated | Helper invoked only from existing successful-run cleanup; tagged live body not run; all regression clients are offline proxies |

Affected targets passed32normalstorage/73independent, exit0. Fullgate recorded separately. No L1/L2/L3 repair, production change or actual cleanup.

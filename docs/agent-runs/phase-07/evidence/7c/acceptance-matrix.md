# Subphase 7C requirement/evidence mapping

| Requirement | Implementation or check | Evidence |
|---|---|---|
| Independent serialized records / corrupt data | HardeningSpec public SDK stubs for6table envelopes, failures, inline/pointer evidence | targeted-3.txt independent73/73 |
| Duplicate keys / metadata / idempotent reload / reader caps | Existing independent ports/loader/Parquet/reader/vector suites retained and rerun | targeted-3.txt |
| N6 S3412 and ledger CAS/cancel | IndependentStorageSdkSpec four additional cases | targeted-3.txt |
| Runtime GraphReader separation | RuntimeGraphFence and fixtures; actual rag/services scan0files | targeted-3.txt; no deployed wiring claim |
| Tagged live suite authored | AwsIntegrationSpec exacttag, bodyguard; helpers in test tree | source-only LiveExclusionSpec3cases |
| Live suite compiles | storage / AwsIntegration / compile | targeted-3.txt and final fixture-targeted-4.txt |
| Excluded from normalcheck | Test-l exacttag versus integration-n; build sentinel; source-onlychecks | live-selection-evidence.txt, full gate result after completion |
| Never executed | All task commands recorded: AwsIntegration compile only; defaultTest-l; no live body lines | commands.md, target logs |
| Real adapter future smoke | ObjectStore/ArtifactRegistry/RunLedger/GraphLoader/GraphReader/VectorStore | Authored only, not live-verified; validated-handle seam explicitly bypasses public export validation |
| Cleanup/cost docs | README Phase7C section with exactownedIDs/versions/hashes, retain-default,5USD proposed incrementalbudget | Authored only; no actual cleanup/cost/IAMclaim |
| Full deterministic gate | JDK17 sbt -batch check | final-check.txt/.json after completion |

N4/N5/N7/N9–N16 remain deferred; N8 remains a process note. N6 can be marked locally covered, with external review closure pending. Phase7 closes only after external approval and human acceptance. No human decision record authored by agents.

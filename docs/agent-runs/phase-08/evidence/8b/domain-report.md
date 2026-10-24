STATUS: COMPLETE for core authorship; targeted gate passed, full gate pending.
OWNER: /root/domain_8b
WORK ORDER: Phase8B additive R1 chunk-group contract.
FILES CREATED: None.
FILES MODIFIED: modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/EmbeddingContracts.scala; modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/EmbeddingContractSpec.scala; modules/core/src/test/resources/wire/embedding-document.json; modules/core/src/test/resources/wire/embedding-work-item.json; modules/core/README.md.
COMMANDS RUN: Owner scoped reads/patches and git diff --check -- modules/core exit0. Coordinator requested format/target command retained in commands.md/core-2.txt, exit0.
TEST RESULTS: EmbeddingContractSpec13passed0failed; two new group contract/validation cases.
VALIDATION RESULTS: chunkCount/wholeTextHash additive; groupKey sixframes excludes ordinal/run/text/count; effectivehash fallback only valid legacy singleton; no key or metadata expansion.
ASSUMPTIONS: Renderer supplies actual whole text hash; storage verifies complete group before writes.
RISKS: A single chunk record cannot establish full-source correctness alone.
MANUAL ACTION REQUIRED: Full gate and independent review.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: Full gate, external review.
NEXT GATE: Coordinator full validation then user-launched read-only review.

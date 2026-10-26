STATUS: COMPLETE authored F1 core repair; verification pending at owner handoff.
OWNER: /root/domain_engineer
WORK ORDER: 8A repair round 1 F1, user-selected stable slot excluding source run ID.
FILES CREATED: None.
FILES MODIFIED: Core EmbeddingContracts.scala, EmbeddingContractSpec.scala, four embedding wire snapshots, README.md.
COMMANDS RUN: Scoped reads/Python edits exit 0; git diff --check exit 0. No sbt by owner.
TEST RESULTS: Eleven core embedding tests authored; coordinator later observed 11/11 in targeted-1.
VALIDATION RESULTS: Seven UTF8 frames type/entity/window/template/policy/ordinal/model tag; no text/documentId/runId in key. Additive slot fields decode defaults empty/-1 but validation rejects incomplete/invalid slots. Real StableIds in fixtures. API coordinated with RAG/storage/test.
ASSUMPTIONS: Renderer supplies actual ordinal and policy version binding algorithm/settings.
RISKS: Source existence/content-ID reconstruction remain owner responsibilities; full/recheck pending.
MANUAL ACTION REQUIRED: Coordinator affected/full gates.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: Verification pending at handoff.
NEXT GATE: Full check then user-launched recheck; no 8B.

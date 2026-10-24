# Repair round 1 — F1 and N1

| Finding / required behavior | Source/test owner and acceptance evidence | Observed result |
|---|---|---|
| F1 stable key independent of text/content ID/source run | Core seven explicit UTF8 frames: type/entity/window/template/policy/ordinal/model tag. Domain fixture uses real content IDs; independent fixed frame expectation and invalid legacy slot decode. | targeted-1 core11/11; targeted-2 independent29/29 |
| F1 real rerendered conflict | RAG + independent actual DocumentRenderer -> EmbeddingManifests.item -> runner, changed source field creates new genuine content ID but same key. Recording embedder/vector/object stores require no extra embed/putBatch/data put, except one rejection-report put. Original vector remains unchanged. | targeted-2 RAG18/18 and independent29/29 |
| F1 unchanged replay | Same real manifest under fresh execution ID skips; zero extra embedding/vector/object puts. | RAG/independent repair suites pass |
| F1 model changes and chunk slots | New model tag yields distinct successful key; two actual rendered chunks have distinct ordinals/keys and replay unchanged. Template/policy versions intentionally identify new namespaces; source run excluded. | RAG/independent repair suites pass |
| F1 valid module fixtures | Storage uses genuine StableIds for actual text with explicit policy/ordinal; changed content ID shares key, conflict pre-embed with only rejection-report object; prepared replay remains covered. | targeted-1 storage13/13 |
| N1 supplied filter identities | fromSummary accepts optional caller identityFields; all five allowed fields preserved through real manifest/runner into vector metadata, invalid fields reject. | RAG/independent repair suites pass |
| N1 exact summary bytes | No/blank abstract preserves original summary Unicode/CRLF/trailing whitespace/qualification text and refs without heading/summary label, before chunking. | RAG/independent repair suites pass |
| N1 explicit permitted abstract | Existing optional paper override composes exact summary + LF + exact abstract, retains text+permission refs and selection; separately documented. | RAG/independent repair suites pass |
| Boundaries | Unchanged StableIds formula, shared core interface, no reverse module dependency, no cloud/provider/8B/reviewer/commit/human-decision edits. | Final scope/hash audit passed;303 frozen files unchanged |

No nonblocking N2-N8 repair was authorized or performed. F1/N1 implementation and local test evidence await independent recheck; implementation agents cannot close their own findings.

Full repaired-tree check: exit0,731/731, real703.88s. No failed test cases; expected injected-failure self-test passed. Independent closure remains pending.

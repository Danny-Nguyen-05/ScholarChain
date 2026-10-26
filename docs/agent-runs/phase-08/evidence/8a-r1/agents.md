# 8A repair round 1 ownership

All agents reuse their original native task IDs and inherited model; exact deployed model build is not exposed. No nested agents or reviewers. Coordinator /root writes phase08 evidence only and executes owner-requested shared gates/formatting.

| Task ID | Role | Exclusive paths | Work order |
|---|---|---|---|
| /root/domain_engineer | domain-engineer | modules/core/** | F1 additive stable slot/key validation/wire fixtures/README/module tests; publish API then free slot. |
| /root/rag_engineer | rag-engineer | modules/rag/** | F1 renderer fills stable slot and context matches; N1 filter metadata + exact summary text/default and explicit abstract composition; module tests/README. |
| /root/storage_engineer | storage-engineer | modules/storage/** | F1 slot metadata composition, valid-document tests and accurate README; preserve immutable dedup/recovery and avoid reverse dependency. |
| /root/test_engineer | test-engineer | tests/** | F1 real renderer -> item -> runner acceptance; N1 independent filter/exact-text checks; migrate only affected synthetic fixtures. |

Shared API handoff: append chunkPolicyVersion:String="" and chunkOrdinal:Int=-1 to document and vector-metadata records; missing defaults decode but fail validation. Key frames type/entity/window/template/policy/ordinal/model tag, excluding text/documentId/source runId. Each owner must coordinate any change before dependent edits.

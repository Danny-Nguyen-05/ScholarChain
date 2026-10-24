# 8B ownership

| Native agent ID | Role | Model | Exclusive write territory |
| --- | --- | --- | --- |
| /root | coordinator | inherited session model | docs/agent-runs/phase-08/** evidence only |
| /root/domain_8b | domain-engineer | inherited session model | modules/core/** |
| /root/storage_engineer | storage-engineer | inherited session model | modules/storage/** |
| /root/rag_engineer | rag-engineer | inherited session model | modules/rag/**; prompts/runtime/**; prompts/schemas/** if needed |

| /root/test_engineer | test-engineer | inherited session model | tests/** |

Native delegation is required by the plan. No nested agents or reviewer launch. Independent test owner is activated after a concurrency slot becomes free. Coordinator may execute owner-requested formatting and gates centrally; authorship remains with each owner. Model's exact version is not exposed by the delegation tool; no invented identifier.

Additional routed owner: `/root/build_8b`, build-engineer, inherited session model, exclusive build.sbt/project/**. Minimal forked RAG CLI lifecycle settings only; existing specialists remain frozen.

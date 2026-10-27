# Subphase 10A delegation

Native agents launched by /root; all inherit the parent session model and reasoning settings. Exact backend model identifiers are not exposed by the collaboration API, so none are inferred. Subagents are forbidden to launch subagents. No reviewer was launched.

| Native ID | Role | Writing territory | Handoffs |
|---|---|---|---|
| /root/build_engineer | build-engineer | build.sbt, project/**, Dockerfile | Cask version, four main classes, test wiring to service/test owners |
| /root/service_engineer | service-engineer | modules/services/** including local tests | API factory to test owner; main classes to build owner; missing contracts to root |
| /root/test_engineer | test-engineer | tests/** | Interface-first independent API acceptance tests; failures routed to service/build owner |
| /root | coordinator | docs/agent-runs/phase-10/** except human records | Assemble reports, retained evidence, reviewer prompt; run full deterministic gate |

# Subphase 10B repair round 2

User explicitly confirmed: “yes fix f6 for me, since it is the blocking bug”. Authorized scope is the F6 residual only. F9 is closed by the external recheck; F7,F8,F10–F16 remain carried and unchanged.

Chosen direction: deterministic explicit graph work budgets strictly below the proxy transport attempt deadline using a configurable response reserve. All node/neighbors/metrics/path operations must consume the forwarded budget, including omitted caller timeout and near-cap values. Preserve narrow GRAPH_DEADLINE_EXCEEDED parsing, no-retry/no-breaker-failure handling, true outage behavior, safe messages and stable cursor binding. Impossible budgets are rejected safely; configuration and API rule documented.

Service-engineer owns modules/services/** for fix/module tests/docs. Test-engineer owns tests/** for actual equal-budget real-GraphApi HTTP regression. Build-engineer owns packaging/local four-image rebuild/eight startup checks/three-main remote-stopgraph checks. Root runs all sbt gates centrally and assembles evidence. Tests first against unfixed code, source-hashed red runs, then production fix and gates. Every sbt command uses exact plan JDK17 environment. Preserve all uncommitted10B/repair1 source. No cloud/provider calls, commits,pushes,reviewer invocation,Phase11 orhuman decision edits.

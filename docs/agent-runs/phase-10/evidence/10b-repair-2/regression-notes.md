# F6 equal-budget regression

Before production edits, both new test suites compiled and ran against repair1 source, after a separate formatting gate. Exact formatted red sources and pre-gate source hashes are retained.

Independent red:3run,1pass,2fail (exit1,7.895s). Both omitted caller timeout and explicit300ms caller timeout against a real GraphApi with graph300ms and proxy300ms caused3snapshot executions for4public requests. The transport timer retried to threshold and opened the breaker. Cursor replay passed. No readiness probe ran between deadline requests.

Module red:4run,0pass,4fail (exit1,6.032s). Observed missing explicit forwarded budget, absent budget configuration validation, invalid caller budget reaching backend, and actual equal-budget DOWNSTREAM_TIMEOUT instead of the typed graph marker. Cask/Undertow also logged a response-already-started exception while the old transport cancellation raced the backend response; full raw log retained.

After root released production edits, the service owner implemented deterministic configured response reserve. Module source then gained a separately reported fifth nondefault-environment case and expanded real node/metric/path guards. The independent EqualBudgetSpec remained byte-identical to its formatted red version. Two existing independent test-double wrappers gained budget-aware overload forwarding; all existing retry/correlation/status assertions remained.

Green targeted:36/36 service tests in6suites and44/44 independent10A/B tests in8suites; packageServices passed (exit0,20.061s). Final full-check results are recorded separately. No expectation was weakened to obtain green.

The final independent cases burst four requests before any readiness call can reset failures, assert exactly4snapshot executions and typed504/nonretryable/callertrace, assertCLOSED before readiness, then readiness200 and normal reads. Omitted and explicit-near-cap budgets both pass. Real signed cursor replay and prior refusal/no-response/unready503 guards pass.

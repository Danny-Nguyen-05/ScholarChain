# F6 regression evidence

Before production edits, both new suites ran against the previously reviewed 10B source. Formatting completed first; each failing run then recorded the formatted source hashes. Exact red test source text is retained as red-GraphRequestDeadlineSpec.scala.txt and red-IndependentServices10BDeadlineSpec.scala.txt.

Independent red: four tests, three passed, one failed (exit1,6.786s). Four public deadline requests caused only three backend calls: the first retried to the threshold and opened the breaker, and subsequent requests were refused. The three real-outage guards already passed. This is observed reproduction of F6, rather than only a static trace.

Module red: five tests, two passed, three failed (exit1,5.142s). The first two failures were the missing request-deadline code/behavior. The third exposed an incorrect new-test assumption that503 contributes to api_downstream_errors_total: the existing metrics contract counts502/504 only. The module test was corrected to retain that prior metric behavior; all OPEN-circuit assertions remained. No unrelated production metrics behavior was changed.

First green: services31/31 in5suites, independent10A/B41/41 in7suites, packaging passed (exit0,11.909s). The independent red test initially remained unchanged through that gate.

Additional test-strengthening review found that interleaved successful readiness calls could reset breaker failures and conceal a partial fix. The independent positive case now sends all four deadline requests before any readiness/successful downstream probe and asserts CLOSED first, then readiness200 and normal success. No required assertion was removed and no production source changed. The first full-check attempt was intentionally cancelled with SIGTERM (exit143,230.240s); its log and source snapshot are retained as check-attempt-1-*.

Final strengthened targeted gate: services31/31 in5suites and independent41/41 in7suites, exit0,9.973s. Final full-check results are recorded separately. The original red source, final test source and all per-gate hashes distinguish the stages honestly.

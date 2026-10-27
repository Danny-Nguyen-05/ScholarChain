# F6 acceptance evidence

The following outcomes were observed in the final strengthened targeted gate (services31/31, independent10A/B41/41). Full-repository results are recorded separately once complete.

| Requirement | Observed evidence |
| --- | --- |
| >=threshold+1 public deadline requests | IndependentServices10BDeadlineSpec sends four requests with threshold3, through real query-api and RemoteGraphApi HTTP to an authenticated local graph stub. |
| Exactly one backend call per deadline | The backend count is exactly4 after the four-request burst; no successful readiness call occurs between them. |
| Typed504 with caller trace | Each response is504, GRAPH_DEADLINE_EXCEEDED, retryable:false and the distinct caller trace for that request. |
| Healthy graph circuit | CLOSED gauge is asserted before any readiness probe can reset the breaker. |
| Healthy readiness and later normal traffic | Readiness200 after the burst; ordinary node and neighbor reads succeed; circuit remainsCLOSED. |
| True transport/unready outages preserved | Separate cases exercise connection refusal, accepted socket with noHTTPresponse and an unready503 service; circuitOPEN and traced readiness503 remain. Further calls are refused without new backend requests. |
| Graph-service actually emits the marker | GraphRequestDeadlineSpec uses a blocked GraphSnapshot and its real20ms local operation budget; returned504 has the distinct nonretryable code. |
| Safe conservative response parsing | Module cases reject retryable, wrong-status, malformed/missing fields, wrong operation/dependency and unknown codes. Raw downstream message is not forwarded. |
| No blanket nonretryable5xx exemption | Only the known status504/code/nonretryable marker, validated for an allowlisted graph operation, receives request-specific treatment. Wrong-status/nonretryable503 still trips the breaker. |
| Actual package and outage behavior | Four current images/eight startup cases and three packaged mains passed; stopping graph kept health200 and produced traced readiness503. |

The pre-fix independent test genuinely failed, with three backend calls for four public requests. Its exact original source is retained. Final test ordering was strengthened after first green, so it is not described as byte-identical to that red version. See regression-notes.md for every failed/cancelled attempt.

F9: README and repairs.md now name the prior observed36/36 six-suite gate and17/17 four-suite gate separately;37 together appeared only within the original full independent625. The new repair targeted gate actually observed41/41 across7suites. No historical log or human decision was rewritten.

F7,F8,F10–F15 remain carried and were not implemented in this round. F12 general graph422 code forwarding is unchanged; only the F6 deadline code is newly handled.

# Carried 10A findings and 10B work

F1 was CLOSED by the user-supplied independent review before 10B. Its Retried Written/Unchanged/Rejected regression suite remains intact and passed in the 10B targeted service gate.

| ID | Prior severity / owner | 10B treatment (pending independent review) | Evidence |
| --- | --- | --- | --- |
| F2 | Medium / service-engineer | Persist terminal errors with retryable:false; document deliberate new workflow requires a new key. | Services10BSpec queue-full and oversized-result cases; prior retry/replay suite. |
| F3 | Low / service-engineer | 202 references report persisted QUEUED/RUNNING state. | Services10BSpec RUNNING replay assertion. |
| F4 | Low / service-engineer | Invalid startup configuration returns exit 2, applied by each main. | Build-owner Docker invalid-configuration checks; final result pending at assembly. |
| F5 | Low / test-engineer and service-engineer | Added failed half-open reopen, queue-full 429, and RESULT_TOO_LARGE module cases. | Services10BSpec; targeted 26/26 passed. |
| O1 | Observation / build-engineer | Rebuild every image after the repaired source and include versioned prompt assets. | packageServices passed; Docker final result pending at assembly. |
| O2 | Observation / orchestrator | Hash sources before every gate, including failed attempts, retain exact logs and commands. | *-sources.json and *-result.json; final source manifest added at handoff. |

No independent reviewer has been invoked and no review approval is claimed for 10B.

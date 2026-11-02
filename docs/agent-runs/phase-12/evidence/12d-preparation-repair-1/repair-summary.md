# Preparation repair round 1 — dispositions pending recheck

This is an implementation report, not independent acceptance. The live 12D spike remains incomplete and blocked.

| Finding | Repair or recorded decision | Remaining limit |
|---|---|---|
| F1, blocking | Actual budget receives course/project/environment/owner plus expiration_date derived from its own end. Configurable ownership values are validated. Exact resource-map, changed-end and blank-tag tests pass; deleting owner in scratch fails the new assertion. Alert thresholds have a user-choice rationale. | Independent recheck; live tagging remains unverified. |
| F2 | Human selected a USD 5 proposed spike cap. The old USD 10 would leave USD 5 from the USD 15 all-EMR reserve; the selected USD 5 leaves USD 10 if fully spent. The original upper-window margin remains USD 5.09. Cost proposal and handoff now state these consequences. | Later EMR runs require a new allocation and exact cost review. No spending authorized. |
| F3 | Budget README discloses deprecated CostTypes and requires credits/refunds exclusion readback after a separately approved apply, or a stop and review of an alternative. | Live accounting behavior unverified. |
| F4 | Spike README says its zero-resource claim is based on source inspection, not constant-output assertions. | No optional static check assigned; no runnable cluster. |
| F5 | Historical metadata omission is recorded in errata. New Terraform records explicitly capture TF_CLI_CONFIG_FILE; new build records capture selected JDK/PATH/logging settings. | Historical missing metadata is not reconstructed as observed. |
| F6 | Seven untracked notes are corrected with original bytes and manifest preserved. Tracked records receive appended readable errata. Historical logs, freezes and inventories are unchanged. | Original gates describe the old source; current freeze/gates are in this repair packet. |
| F7 | Human chose neutral references in new material and preservation of existing records/history. | No historical redaction or history rewrite authorized or performed. |

Offline native results: course 40 passed, billing 7 passed, proposal 6 passed; total 53 passed / 0 failed, 71 assertions and 27 expected-failure runs. Missing-owner RED: init exit 0; test exit 1, 6 passed / 1 failed at the intended actual-resource tag assertion. No development failures. Static guard inspected 69 source files with zero findings; its four self-tests passed. The existing guard does not scan .tftest.hcl fixtures; the synthetic address/account fixtures remain unchanged in character.

The final 203-file source freeze precedes the new full JDK 17 gate. The full build passed; exact fresh XML counts, timestamps and hashes are in gate-summary.json and build/build-result.json. B1/B2/B3/R1 and carried 12C items including N19/N20 are unchanged. Pins and all three lock files are unchanged.

Live prerequisites remain: active account-wide monitor and recipient proof; usable cost data with conservative pending charges; separate non-root temporary deployment access; portable G1 bundle; same-JAR local baseline; actual driver/executor class origins; shared-filesystem proof; independent elapsed-time termination; genuine isolated plan/checksum/review; human-written exact execution and teardown approval. Planner stays read-only. No account/paid call, real plan/apply/destroy/import, credential/state/private-input read, reviewer launch, commit, push or Phase 13 work occurred.

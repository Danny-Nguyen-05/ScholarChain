# Historical preparation handoff — corrected notes

> Updated during preparation repair round 1. Original bytes are preserved in `../12d-preparation-repair-1/original-notes/`. Earlier gates describe the pre-repair state; use the repair packet for current source and gate results.

**Status:** the original local preparation gates passed; live 12D remains blocked. This file has been corrected for F2/F6. The current repair handoff and review prompt are in the separate repair packet when complete.

Original branch/base/HEAD: phase-12 at 5ca8406bad5fe55f732458fa0cbd5d561ac83d8f. The original footprint was four modified tracked records and 95 untracked files; its exact historical inventory is handoff-files.json. No commit or push occurred. Current repair changes must be assessed against the repair preflight, not this old inventory.

The billing root was originally untagged (F1). The repair adds the five required tags, with expiration tied to the budget's own retention/reconciliation end. The bootstrap remains disabled and unapplied. The EMR directory is a nonlaunchable contract with zero AWS resources by source inspection, not by the constant-output assertion alone.

## Allocation consequence

The USD 15 reserve covers all EMR spikes and experiments. The former USD 10 spike proposal would leave USD 5. The user now chose USD 5, leaving USD 10 of that reserve if fully spent. Neither split adds money to the shared USD 200 ceiling. The 12C upper-window margin remains USD 5.09. Later EMR work requires a new allocation and exact cost decision. The USD 0.96 compute subtotal is not an all-in estimate or approval to spend.

## Original observed checks — pre-repair

| Check | Original result |
|---|---|
| Terraform init/fmt/validate/test in three roots | All 12 final commands exited 0 |
| Mock plans | 51 passed, 0 failed; 69 assertions; 26 expected-failure runs |
| Credit mutation | Init 0, test 1; 4 passed / 1 failed at intended assertion |
| Static guard | 69 files, 0 findings; 4 self-tests passed |
| JDK 17 sbt check | Exit 0; 1,255 tests in 157 fresh XML; 0 failures/errors/skips |
| Build interval | 2026-10-30T21:52:13.133933Z–22:04:25.322439Z |
| Wall time | 732.205371 seconds; sbt reported 730 seconds |
| Original integrity | 203 frozen files and 1,377 snapshot files unchanged across that gate |

One stale TestRunMarkerSpec XML report under project/verification/target was excluded. Only the expected checkProbeInjectFailure error block appeared.

Original commands and log hashes remain byte-identical in infra/final-commands.json, coordinator/commands.json and build/commands.json. The original Terraform records omit an environment field (F5); prose names TF_CLI_CONFIG_FILE but does not retroactively supply observed metadata. New repair records capture selected non-secret environment values explicitly.

The original gate used JDK 17 with JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home, PATH prepending JAVA_HOME/bin, and SBT_OPTS pointing to docs/agent-runs/phase-04/xml-repair-logback.xml, followed by java -version and sbt -batch check. The original compressed log and raw SHA remain in build/build-result.json.

Original source-freeze.json and final-integrity.json describe the historical state. They are preserved, not regenerated to hide the authorized repair delta. The old evidence manifest is archived in ../12d-preparation-repair-1/original-notes/; the refreshed manifest accounts for these readability corrections. Current source and build validation belongs to the repair packet.

Remaining live prerequisites are listed in launch-dependencies.md and next-steps.md. No account API, real plan/apply/destroy/import, paid call, IAM elevation, human approval file, reviewer launch, commit, push or Phase 13 work occurred.

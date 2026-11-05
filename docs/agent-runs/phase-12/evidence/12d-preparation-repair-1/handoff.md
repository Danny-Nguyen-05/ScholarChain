# Phase 12D preparation repair round 1 handoff

**Status:** offline repair and gates complete; independent recheck pending. The live spike remains blocked and has not run.

Branch: phase-12. Base/HEAD: `5ca8406bad5fe55f732458fa0cbd5d561ac83d8f`. Footprint: 5 modified tracked records and 183 untracked files; exact paths are in handoff-files.json. Relative to the repair preflight, 21 existing files changed: eight isolated infrastructure files, seven untracked preparation notes plus their manifest, and five append-only phase records. The other 3,998 baseline files are unchanged. Human records, main source, application/build files, pins and locks are unchanged.

## Repairs and choices

F1: the actual budget now carries course/project/environment/owner and expiration_date derived from its configured retention/reconciliation end. Tests verify synthetic tag values, a changed end date and blank-value rejection. The missing-owner mutation fails at the new actual-resource assertion. Thresholds have a user-choice rationale comment.

F2: the USD 15 reserve covers all EMR spikes and experiments. The old USD 10 proposal would leave USD 5. The user selected a USD 5 proposed cap, leaving USD 10 if fully spent. The upper-window margin remains USD 5.09. Later EMR runs require another allocation and exact cost decision; no spending is approved.

F3–F6: deprecated CostTypes/readback and source-inspection limits disclosed; new command records include selected non-secret environment; original missing metadata is acknowledged, not reconstructed; readability corrections preserve original bytes and append tracked errata. F7: neutral future references, existing records/history preserved by user choice. See repair-summary.md and errata.md.

## Observed gates

| Check | Result |
|---|---|
| Three-root init/fmt/validate/test | All 12 final commands exited 0 |
| Native tests | 53 passed / 0 failed; 71 assertions; 27 expected-failure runs |
| Missing-owner RED | Init 0, test 1; 6 passed / 1 failed at intended tag assertion |
| Static guard | 69 files, zero findings; four self-tests passed |
| Full JDK 17 gate | Exit 0; 1,255 tests, 157 fresh XML, zero failures/errors/skips |
| Gate interval | 2026-10-31T02:37:36.916331+00:00–2026-10-31T02:50:16.799986+00:00 |
| Gate wall time | 759.886027 seconds; sbt reported 751 seconds |
| Integrity | 203 frozen files and 1,377 broader snapshots unchanged |

Exact Terraform argv/cwd/selected environment/times/log SHA are in infra/final-commands.json. Each of the course, billing and proposal roots ran `/tmp/scholarchain-phase12b-repair1-infra/terraform` with `TF_CLI_CONFIG_FILE=/tmp/scholarchain-phase12b-repair1-infra/terraformrc`, followed by init -backend=false -input=false -no-color -lockfile=readonly; fmt -check -recursive; validate -no-color; test -no-color.

The full repository gate used JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home, PATH prepending JAVA_HOME/bin, and SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml, then java -version and sbt -batch check. Exact selected values are in build/commands.json. One stale XML report is separately inventoried; only the expected checkProbeInjectFailure error block appeared.

Freeze SHA: `b11ccf2891d31dce9150cfde4c37c8e4da0b49b1ba2209cc6afaea980f428123`. Raw build SHA: `20ca0ec03b1d92a46b02bd384178ec8a43a5fffa26e6bc414bf432e9c2e6019e`. Gzip SHA: `a16df5b1ac1dbcd51d3466ef810a6243cffbf4c0e8d963cbb05331e0f2e30889`. Verification: coordinator/final-integrity.json, infra/retention-manifest.json, build/artifact-manifest.json and evidence-manifest.json. The raw log is retained once as gzip. All 80 original preparation artifacts remain verifiable using archived original notes for corrected items. Historical gate results are not relabeled as current passes.

## Remaining gates and human action

User launches the independent preparation-only recheck using ../../reviewer-prompt-12d-preparation-recheck-1.md. After APPROVE, the human must select a bounded continuation, such as read-only real planning for the budget bootstrap or Spark/build technical readiness. No continuation is selected or started automatically.

All live prerequisites remain: active monitor and private recipient proof; usable cost data and conservative remaining allowance; separate non-root temporary deployment access; portable G1 and same-JAR baseline; real driver/executor origins; shared-filesystem proof; independent elapsed-time deadline; actual isolated plan/checksum/review; and human-written exact execution/teardown approval. Planner stays read-only. B1/B2/B3/R1 and N19/N20 are carried unchanged. No account/paid calls, real plan/apply/destroy/import, credentials/state/private-input reads, human approval writes, reviewers, commits, pushes or Phase 13 work occurred.

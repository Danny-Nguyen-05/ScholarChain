# Phase 12A evidence

Read `../../owner-report.md` and `../../test-report.md` for scope and results. `step-0-answers.md` records user setup answers; no human gate or ratification record was authored here.

- `infra-command-manifest.json`, `infra-final-command-results.json`: exact Terraform gate commands, cwd, exit codes, historical development failures and log hashes. Logs originally at `/tmp/scholarchain-phase12a-infra-*.log` are retained here as `infra-*.txt` with unchanged bytes.
- `infra-coverage.json`, `infra-test-2.txt`: final 13/0 mock plan-only runs, 27 assertions, 6 expected-failure cases. `infra-test-1.txt` retains the earlier 11/0 result and warning.
- `infra-owner-report.md`, `infra-manual-checklist.json`, `infra-native-vector-schema-check.json`: owner report and limited manual/schema findings; no scanner pass or independent security approval.
- `terraform-cli-install.json`, `terraform-1.13.5-official-checksums.txt`: isolated CLI provenance. Raw full provider schema stays in /tmp; its checksum is in the command manifest, and the small relevant resource-schema proof is retained.
- `build-start.json`, `build-result.json`, `build-validation.json`, `build-owner-report.txt`, `build-ignore-checks.json`: JDK17/sbt environment/results, fresh XML hash/count inventory, and 33 ignore assertions.
- `sbt-check.log.gz`: full durable raw sbt output, compressed to keep evidence lean. `sbt-log-integrity.json` gives compressed and decompressed SHA-256/bytes. `build-sbt-check-excerpt.txt` retains summaries and expected gate probe. Read compressed output with a read-only gzip reader; no builds need to be rerun by reviewer.
- `build-evidence-reconciliation.json`, `coordinator-validation.json`, `infra-source-freeze.json`: source/test counts and checksum reconciliation. `handoff-files.json` is the exact final changed/untracked list. Source freeze is limited to authored files, not state/provider cache.
- `authority-reading.json`, `ownership-and-reading.json`, `preflight.json`: source provenance, branch/base, delegation and disclosed course/plan differences.

There is no live AWS plan, state, credential content, actual account inventory, paid model output, or live cost estimate in this evidence. Local state and plan artifacts must remain ignored. No AWS account is required until12C (or earlier approved12D).

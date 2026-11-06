# Phase 13 work order

Plan: `/Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase13.md` (Phase 12 handoff section added 2026-11-05 is binding).
Tool: Claude Code orchestrator (main session), subagents launched with model `sonnet` (Sonnet 5.5), effort `high`, at the user's request.

## Subphase 13A — check, package, plan, deploy, rollback, cleanup

Scope: Subphase 13A only. No AWS mutation, no live plan, no apply, no reviewer launch, no commit or push.

### Preflight (observed 2026-11-05)

- Branch `phase-13`; base SHA `8bee663040ba4e66b1edc1676d5346621c3f7384`; `git status --short` empty.
- `java -version` (JDK 17 env): `openjdk version "17.0.20.1" 2026-08-18` (Homebrew build 17.0.20.1+0).
- `shellcheck` 0.11.0; `terraform` v1.13.5 (`/opt/homebrew/bin/terraform`, tfenv); Docker server `linux/arm64` 29.5.3; host `arm64`; Python 3.14.5; aws-cli 2.35.4.
- G5 runtime tgz `target/phase12d-runtime-repair-20261103/artifacts/scholarchain-spark3.5.4-scala2.13.14-java17-runtime.tgz`: size `321876735` bytes; `shasum -a 256` = `789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5` (matches decision 12-10).

### Step 0 answers (user, 2026-11-05, recorded verbatim in substance)

1. **13-1 Docker:** Docker Desktop is running. `package.sh` builds the images locally; the ECR push lives only in `deploy.sh` (dry run). Build for `linux/amd64`: ECS uses `cpu_architecture = "X86_64"` (`infra/terraform/modules/runtime/compute.tf:45`) and the Mac is arm64. Read the platform from config, not a constant, and add a check that fails if the built image architecture differs from the ECS task's. If Docker isn't reachable, fall back to jars plus a static Dockerfile check, and disclose it.
2. **13-2 Deploy approval:** default accepted. `deploy.sh` reads `docs/agent-runs/phase-14/human-gate.md` (`APPROVED_PLAN_SHA256`, commit, account, region lines); refuses on a dirty tree or any mismatch.
3. **13-3 Language/lint:** Bash `set -euo pipefail`, `python3` allowed for structured checks. shellcheck is installed; use it on every script and fail `check.sh` on any shellcheck finding.
4. **13-5 Rollback:** default accepted. App rollback = redeploy previous image digests from the release manifest; infra rollback = re-plan/re-apply the previous commit's plan with the human gate; no data repair.
5. **G1 S3 I/O:** option (ii), EFS staging plus S3 copy steps.
6. **G5 runtime archive:** user keeps a Drive copy. Record size and sha256 in evidence, re-verify the sha256 in preflight, put the S3 location in a config variable. Upload nothing before Phase 14.
7. **G6 EMR budget:** allocate USD 9.50 of the EMR reserve to Phase 15; hold back about USD 5 for possible charges from the 5 PendingDeletion KMS keys. Per-run cap USD 3, maximum 3 live EMR runs. Enforce through runtime and capacity caps; print the estimate before any `--execute`. User revisits after the keys delete (about 2026-11-11) and the Billing page settles.
8. **Account in approval record:** `APPROVED_ACCOUNT_SHA256` = lowercase hex sha256 of the 12-digit account ID string with no trailing newline (`printf '%s' "$id" | shasum -a 256`). `deploy.sh` computes it the same way and never prints the raw ID.
9. **Terraform:** 1.13.5 via tfenv on PATH. `TERRAFORM_BIN` overrides; scripts fail clearly unless the version is exactly 1.13.5 (matching `required_version`).
10. **Timeout helper:** python3 helper in `scripts/lib/`; must kill the whole process group. In 13A use it only for timeouts; the YARN application kill (item 1) is 13B.

Accepted assumptions: 6A F6 (packaging JDK guard) goes to `build-engineer` in 13A; `check.sh` runs the full `sbt -batch check` on JDK 17; plan files stay git-ignored with only checksums in evidence; no reviewer and no commits by agents.

### Mid-subphase decisions (user, 2026-11-05, via the orchestrator's question after the infra-engineer first report)

- **Base Terraform test defect:** `infra/terraform/tests/phase12b.tftest.hcl:136` (R1 route-ownership assertion) scans `fileset(path.module, "**/*.tf")`, which since Phase 12D (`f52b981`) includes `infra/terraform/spikes/emr-spark-isolated/network.tf`; root `terraform test` fails 1/40 on the clean base. **Decision: fix now in 13A.** Scope widening: `infra-engineer` may edit only that assertion's fileset to exclude the separate `spikes/` roots, plus a negative case proving a route resource outside `modules/network` (and outside `spikes/`) still fails.
- **Approval-record dirty-tree exemption:** accepted. Only the exact approval-record path is exempt from the dirty-tree refusal; any other uncommitted or untracked file still refuses.
- **`check.sh` PARTIAL:** use a distinct nonzero exit code for `RESULT: PARTIAL` so a partial run is never mistaken for a pass; update tests and docs.
- **Phase 14 flow:** accepted as designed. Keep the `ecr-repositories-exist` refusal (first deployment = approved base apply with runtime disabled, then image push, then the runtime plan; document it in `scripts/README.md`) and the two-stage `rollback.sh --execute` (plan, then deploy after a new human approval record).

- **Orchestrator repair item (not a user decision):** integrity and safety pins in `scripts/config/release.conf` must not be overridable by a same-named environment variable. Tests must use an explicit, announced test-only config file instead.

### Repair-round decisions (user, 2026-11-05)

- **Round 1, F5:** the human writes a pre-spend receipt named by `APPROVED_PRESPEND_SHA256`. Maximum age 24 h; minimum headroom USD 20; missing cost data is never treated as zero.
- **Round 1, F3:** preserve state, all S3, S3 Vectors, the KMS keys that keep preserved data readable, and the grading log groups. Tear down the ECS/ECR runtime, EMR, Neptune, DynamoDB, SQS, Step Functions and the network. Details are in `repairs.md`.
- **Round 2:** fix all blocking findings.
- **Round 3, S1:** option (a). Infrastructure rollback keeps the running runtime by carrying the deployed image revision. The revision is bound to a verified previous deploy manifest or push record, its registry digests are checked before apply, and the four ECS services are re-verified afterwards.

- **Round 3, verification scope:** this round changes only `scripts/**`. Run the clean-snapshot `check.sh` with every gate except sbt, and reuse the last passing `sbt check` (repair round 2: 742 s, 0 failed). Record proof that no Scala or build input has changed since then. Run the full seven-gate check once, after reviewer approval and before the user's commit.

Still pending human decisions: A2; the approval-format additions (`APPROVED_RECEIPT_SHA256`, `APPROVED_ENVIRONMENT`, the `cleanup-prepare` stage, `cleanup --confirm --plan`); the live-state location.

### Routing

| Agent | Paths | Task |
|---|---|---|
| `build-engineer` | `build.sbt`, `project/**`, `Dockerfile` | 6A F6: Java 17 guard on every packaging task; a single release-packaging alias for `package.sh`; build-owned tests |
| `infra-engineer` | `scripts/**` | `check.sh`, `package.sh`, `plan.sh`, `deploy.sh`, `rollback.sh`, `cleanup.sh`, `scripts/lib/**`, `scripts/config/**`, `scripts/tests/**`, `scripts/README.md` |
| orchestrator | `docs/agent-runs/phase-13/**` (except human-owned files) | evidence assembly, reports, reviewer prompt |

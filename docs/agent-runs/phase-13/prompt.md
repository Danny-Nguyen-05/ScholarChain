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

## Subphase 13B — smoke, bounded pipeline (Hadoop, ER, Spark), experiment, archive

Scope: Subphase 13B only. No live AWS action, no real plan or apply, no reviewer launch. Subagents use model `sonnet` (Sonnet 5.5), effort `high`, at the user's request.

### Preflight (observed 2026-11-06)

- Branch `phase-13`. 13B base SHA: `52c2e2178662d98103387483b82cd775dc713445`. That is the 13A commit, which the user asked the orchestrator to commit and push to `origin/phase-13`.
- `git status --short` was empty.
- `java -version` (JDK 17 env): `openjdk version "17.0.20.1" 2026-08-18`.

### Step 0 answers (user, 2026-11-06: "Use all defaults")

1. **Smoke-test target.** Two levels:
   - a local stub server for fast failure-path tests;
   - one real local run against `query-api` in `SCHOLARCHAIN_SERVICE_MODE=offline-synthetic`. It covers health, readiness, the supported fixture question, an evidence fetch, a repeated request with the same `Idempotency-Key`, and one expected 401.
2. **Smoke API key.** The test generates a throwaway key, and only its sha256 reaches the service. `smoke-test.sh` reads the key from an environment variable (for example `SCHOLARCHAIN_SMOKE_API_KEY`) and never prints it.
3. **Pipeline step form.** Three steps run on the Terraform-created cluster, and the script creates no infrastructure:
   - Hadoop prep: `HadoopPrepMain`, as in Phase 4.
   - Entity resolution: `Phase5Main`, a single-JVM step on the master using the bootstrap Java 17.
   - Spark: the Phase 6 job via `spark-submit`, YARN cluster mode, with the decision 12-10 settings and a driver and executor class-origin check first.

   Data moves EFS ⇄ S3 through copy steps (G1 option ii).
4. **G6 caps.**
   - The cost estimate is instances × reviewed hourly rate × maximum runtime.
   - A run is refused when its estimate exceeds USD 3, when 3 live runs are already used, or when the cumulative total would exceed USD 9.50. The estimate is printed before any `--execute`.
   - Rates live in config with their pricing source URL and retrieval date. They are read from public pricing pages (read-only), and the human confirms them. Until the human confirms, `--execute` is refused.
   - The run count is kept in an ignored local ledger.
5. **Pipeline and experiment approval record.** The same `KEY=value` format as 13A, at a path passed by flag. It names the manifest hash, budget, region, maximum capacity, maximum runtime and teardown, plus a pre-spend receipt.
6. **Experiment manifests.**
   - The schema lives with the scripts, and the tests use fixture manifests only.
   - Real manifests are written in Phase 15 by `experiment-engineer` under `experiments/`.
   - "Committed" means tracked and unchanged at HEAD. A manifest without budget and teardown sections is rejected.
7. **Evidence archive target (13-4).**
   - Small files go to `docs/agent-runs/phase-NN/evidence/`.
   - Files over 1 MB get a sha256 and a recorded Drive or S3 location instead of being committed.
   - The S3 prefix is dry-run only.
8. **Carried item 1.** Each run tags its YARN application with the run ID, and the hard runtime cap kills that application by tag, not only the client. The cluster's auto-termination stays set.
9. **Carried item 31.** New archives are built without macOS `._` metadata files. The same fix goes into `scripts/phase12d-spike/collect-evidence.sh`.
10. **test-engineer.** Independent tests go under `tests/scripts/` (Python). infra-engineer adds that folder as a required suite in `check.sh`.
11. **Subagent model.** The default was Opus 5.5 high. The user then chose **Sonnet 5.5 high**.
12. **Verification.** Fast checks during the work, then one full seven-gate clean-snapshot `check.sh` and a JDK 17 `sbt check` at the end.

### Routing (13B)

| Agent | Paths | Task |
|---|---|---|
| `infra-engineer` | `scripts/**` | `smoke-test.sh`, `run-bounded-pipeline.sh`, `run-experiment.sh`, `archive-evidence.sh`; items 1 and 31; `scripts/tests/**`; README; adding `tests/scripts` as a required suite in `check.sh` |
| `test-engineer` | `tests/scripts/**` | independent dry-run tests with fake binaries |
| orchestrator | `docs/agent-runs/phase-13/**` | evidence, reports, reviewer prompt |

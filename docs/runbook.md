# ScholarChain runbook

Operating guide for the human operator: deployment, smoke tests, the bounded data run, common failures, rollback, incident escalation and cleanup. It is a map into the detailed runbooks, not a replacement for them:

- Step-by-step live session with every command and "if it fails" rule: [docs/runbooks/phase-14-live-session.md](runbooks/phase-14-live-session.md) (Session 1 text, with amendments for Session 2) and [docs/runbooks/session-2-plan.md](runbooks/session-2-plan.md) (the Session 2 plan and decision record).
- Every script, flag, exit code and approval point: [scripts/README.md](../scripts/README.md).
- Terraform inputs, modules and local checks: [infra/terraform/README.md](../infra/terraform/README.md); deployer stack and role removal: [infra/terraform/deployer/README.md](../infra/terraform/deployer/README.md).
- Incident records: [docs/incidents/README.md](incidents/README.md).
- Components and their limits: [docs/architecture.md](architecture.md), [docs/service-limits.md](service-limits.md), [docs/threat-model.md](threat-model.md); HTTP routes: [docs/api.md](api.md).

## 0. Replay status of this file

Replayed in package 17A-1, 2026-11-22 (offline, read-only): `bash scripts/<name>.sh --help` for `check`, `package`, `plan`, `deploy`, `rollback`, `cleanup`, `smoke-test`, `smoke-local`, `run-bounded-pipeline`, `run-experiment`, `archive-evidence`, `upload-slice` and `upload-emr-artifacts`: each exited 0 and printed its usage text (between 43 and 190 lines). Everything else below is copied from the committed scripts README, the committed runbooks and the Session 2 evidence. Package 17G then replayed part of this file on a fresh clone of `main` at `d1d4fe7` (JDK 17, offline, 2026-11-22); each section below states what that replay observed. Nothing here reports a result that was not already in a committed record.

## 1. Ground rules

- All AWS infrastructure is authored and changed through Terraform. No console or CLI mutation is an implementation path ([AGENTS.md](../AGENTS.md)).
- Apply, deploy, rollback, scale changes, data destruction and security changes each need a written human approval record, a fresh pre-spend receipt and (for plan stages) the checksum of the reviewed plan. The cloud scripts print their commands and run nothing unless `--execute` is given.
- When an `--execute` command fails, stop. Do not retry blindly: a retry can repeat a paid action or a half-finished change. Save the named log and send only file paths and the marker lines (`STEP:` and `RESULT:`) to the coordinator, never an account id, e-mail address, key, private variable value, plan text or the contents of `~/.aws` ([runbook rule](runbooks/phase-14-live-session.md), "How to use this runbook").
- Keys are entered by the human into Secrets Manager (or an environment variable for one command) and revoked after cleanup. No secret value goes into a tracked file.
- Region is `us-east-2` ([service limits](service-limits.md), section 1). Times are written in UTC with Chicago time where useful.

## 2. Prerequisites

From [scripts/README.md](../scripts/README.md), "Prerequisites": JDK 17 (a newer default JDK makes the Hadoop tests fail), sbt, Terraform exactly 1.13.5 (any other version is refused with exit 3), Docker with buildx for `package.sh`, `shellcheck`, `python3` (standard library only), `git`, `shasum`, and the AWS CLI for `--execute` paths. `terraform init` downloads the pinned provider and makes no AWS API call. Settings live in `scripts/config/release.conf`; names of the environment variables the scripts read are listed in the scripts README ("Settings and environment variables").

## 3. Local verification (no cloud)

```bash
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"   # macOS; the scripts also apply JDK 17 themselves (scripts README, Prerequisites)
scripts/check.sh                       # gates: constitution, hooks, shell, python, terraform, script-tests, sbt
sbt check                              # repository definition of done; writes the test marker only on success
scripts/package.sh                     # jars, four linux/amd64 images, release manifest under target/release/<commit>/
scripts/smoke-local.sh --build         # starts query-api in offline-synthetic mode on loopback, runs the smoke test, stops it
```

Last recorded full check before this phase: `RESULT: PASS gates=7` for the Phase 17 starting commit ([docs/agent-runs/phase-17/prompt.md](agent-runs/phase-17/prompt.md)). 17G observed on the clone: `sbt -batch clean check` passed (1,773 tests succeeded, 0 failed, 2 canceled, sbt total time 14:48), `sbt -batch fmt` left the tree unchanged, `compile` and `packageRelease` succeeded, and `bash scripts/plan.sh --env course --region us-east-2` ended `RESULT: DRY-RUN no aws or terraform command was run and no file was written; re-run with --execute (approval point 4) to plan` (without `--region` it is refused with exit 2). The result of the full `scripts/check.sh` on the clone is in `docs/agent-runs/phase-17/17g-replay.md`. `bash scripts/package.sh` was not replayed (the Docker daemon was not running). Terraform checks without an account, from `infra/terraform`: `terraform init -backend=false -input=false`, `terraform fmt -check -recursive`, `terraform validate`, `terraform test` ([Terraform README](../infra/terraform/README.md)); they run in the terraform gate of `scripts/check.sh` and were not run separately in 17G.

The plan for the course environment is made by `scripts/plan.sh --env course --region R --profile P --execute` (read-only; it never applies). The archived plan checksum and receipt belong in the release manifest.

## 4. Deployment

### 4.1 Order, as recorded in the scripts README

The first deployment is five separate steps, each with its own approval record and pre-spend receipt ([scripts/README.md](../scripts/README.md), "First deployment (Phase 14)"):

1. `scripts/plan.sh --env course --region R --profile P --execute` with the runtime disabled (the base plan). Review `PLAN-TEXT` and the `PLAN-ACTION` list, write the pre-spend receipt and approval record A, then `scripts/deploy.sh --stage base-apply --plan <base plan> --region R --profile P --execute`. This creates the ECR repositories and uploads the runtime archive.
2. `scripts/package.sh` at the same clean commit.
3. Approval record B and a fresh receipt, then `scripts/deploy.sh --stage push --region R --profile P --execute`. Images are pushed by commit SHA and registry digests are verified against the push record.
4. `scripts/plan.sh --env course --region R --profile P --image-revision <HEAD SHA> --execute` with the runtime variables enabled in the private variable file (the runtime plan).
5. Approval record C, a fresh receipt, then `scripts/deploy.sh --stage runtime-apply --plan <runtime plan> ... --execute`. The script verifies the four ECS services and their task definitions.

Not replayed in 17A or 17G: the live replay needs an AWS account and a human gate and is outside the offline packages. Neptune, EMR and the HTTPS listener are enabled by variables in the private tfvars file and went in as separate applies in Session 2 (see the table below). The deployer stack (`infra/terraform/deployer`) must be applied first because it holds the permission boundaries; a Bedrock run additionally needs the matching deployer variables before the base plan ([provider-fallback.md](report/provider-fallback.md), section 4).

### 4.2 What Session 2 did (2026-11-18, UTC)

From the [decision log](agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md) and [INDEX.md](agent-runs/phase-15/evidence/session-2/INDEX.md):

| Time | Step | Result |
|---|---|---|
| 14:04 to 14:14 | IAM window 1; deployer apply | 13 resources added (operator roles) |
| 14:47 | base plan | 171 to add, action list identical to the reviewed derivation |
| about 15:04 | base-apply 1 | Terraform applied; runtime-archive upload failed with `RequestTimeout` ([incident](incidents/2026-11-18-base-apply-runtime-archive-requesttimeout.md)) |
| 16:09 | base-apply 2 | passed; the upload took about 52 minutes with `s3.max_concurrent_requests` 2 |
| 16:21 | EMR artifact upload | 17 files verified |
| 16:32 to 17:06 | bounded pipeline on EMR (size S) | stage-in, Hadoop prep, entity resolution and the class-origin step completed; the Spark step failed ([incident](incidents/2026-11-18-emr-spark-job-step-emrfilesystem.md)) |
| 17:04 | render-only vector documents from the local S export | 10,000 documents |
| 18:20 | ingest 1 | all 10,000 rejected, HTTP 401 ([incident](incidents/2026-11-18-vectors-ingest-1-voyage-401.md)) |
| 19:11 | ingest 2 | 10,000 written, 0 rejected |
| 19:12 | query smoke | 5 of 5 samples |
| 20:01 to 20:21 | Neptune base apply | passed |
| 20:14 | image push | passed |
| 20:28 | runtime apply | passed; four services at 1 of 1 |
| 20:36 | smoke (healthz, readyz) | 2 of 6 checks by design, both 200 |
| 20:43 to 20:52 | load test | aborted on a 503 and 504 burst ([incident](incidents/2026-11-18-rb-load-test-abort-5xx-burst.md)) |
| 21:37 to 21:46 | failure injection | two stop-task events; recovery 113 s and 68 s |
| 21:48 | evidence archive | written and verified |
| 21:50 to 22:44 | cleanup | see section 9 |

Run IDs: the EMR run is `15a-emr-size-100-20261118T163203Z-87466`; the stores and the answer key use the local export `run:ba7402d1-959a-4277-8c6e-e92878a38afa` ([docs/data-lineage.md](data-lineage.md)).

## 5. Smoke tests

`scripts/smoke-test.sh` reads the API key from the environment variable named by `--api-key-env` (default `SCHOLARCHAIN_SMOKE_API_KEY`); it never prints it, and refuses plain `http://` to a non-loopback host. Six checks: `healthz`, `readyz`, `query`, `evidence`, `idempotency`, `error-path`; `--checks` selects a subset; `--semantic route` adds the public semantic route check.

```bash
read -rs SCHOLARCHAIN_SMOKE_API_KEY && export SCHOLARCHAIN_SMOKE_API_KEY   # value is typed, not echoed
scripts/smoke-test.sh --url https://<endpoint>                # the real query smoke needs the live model key in the runtime
scripts/smoke-test.sh --url https://<endpoint> --checks healthz,readyz
scripts/smoke-local.sh                                        # loopback, offline-synthetic, throwaway key
```

Not replayed against a deployed host in 17A or 17G (no deployed stack exists). In 17G the local equivalent, `bash scripts/smoke-local.sh --build`, ended `RESULT: PASS local offline-synthetic query-api passed all smoke checks (the six plus the semantic route and its cache counter) on 127.0.0.1:<port>`. Recorded results: Session 2 ran only `healthz,readyz` (both 200) because the Anthropic secret held a placeholder; the missing and invalid key gave 401 and an unknown evidence id gave 404 ([smoke-14b.log](agent-runs/phase-15/evidence/session-2/rb-runtime/smoke-14b.log), [manual-401.log](agent-runs/phase-15/evidence/session-2/rb-runtime/manual-401.log)). Session 1 passed all six checks against the live model ([phase-14 human gate](agent-runs/phase-14/human-gate.md), B8.8 and B12). The route contract the smoke follows is in [docs/api.md](api.md).

A manual query, once the key is in the environment (synthetic question; no result is claimed here):

```bash
curl -sS -X POST "https://<endpoint>/v1/query" \
  -H "Authorization: Bearer $SCHOLARCHAIN_SMOKE_API_KEY" \
  -H "Idempotency-Key: demo-$(date +%s)" -H "Content-Type: application/json" \
  -d '{"question":"Synthetic fixture: publication count for A","output":{"includeScores":false}}'
```

Not replayed against a deployed host in 17A or 17G (no deployed stack exists). A 202 reply is followed with `GET /v1/jobs/{jobId}` and `/result`; `/v1/explain/{queryId}` and `/v1/queries/{queryId}/evidence` give the audit.

## 6. Bounded data run

Two committed paths exist for the size S slice (10,577 works; [data-lineage](data-lineage.md), section 2).

**Local, no cloud.** `scripts/lib/p6_local_chain.py` runs the exact six EMR steps (stage-in, hadoop-prep, entity-resolution, spark-class-origin, spark-job, copy-out) by calling the unchanged `scripts/emr/sc-step.sh`, with local stand-ins for YARN and S3:

```bash
python3 -I scripts/lib/p6_local_chain.py run --size S --root target/phase15/p6 --retain
```

Inputs it needs are listed by `python3 -I scripts/lib/p6_local_chain.py --help` (replayed in 17A and again in 17G: exit 0; the options named above are from that text): the four packaged jars from `sbt packageEmr`, the Hadoop client classpath, the S input tree under `target/experiment-inputs/15a/`, the portable runtime archive and JDK 17. The run itself was not replayed in 17A or 17G: it needs the pinned runtime archive and the Hadoop client classpath file. The recorded S run produced `run:ba7402d1-959a-4277-8c6e-e92878a38afa`; its timings are in [performance-metrics.md](../experiments/results/phase16/performance/performance-metrics.md) (last passing S run: Hadoop prep 36.73 s, entity resolution 96.7 s, Spark job 362.87 s, local wall times on one laptop).

**EMR.** `scripts/run-experiment.sh --manifest experiments/manifests/15a-emr-size-100.json --cluster-id J-ID` runs only a committed, unchanged, valid manifest and delegates to `scripts/run-bounded-pipeline.sh`, which submits six steps to an existing Terraform-created cluster and never creates infrastructure. Its dry run is the default; `--execute` is a human approval point (budget: USD 0.84, 75 minutes, idle timeout 900 s). The recorded outcome is that the Spark step failed on `EmrFileSystem`; the fix is an open item and no EMR run has completed end to end ([incident](incidents/2026-11-18-emr-spark-job-step-emrfilesystem.md)). Record the cost with the ledger step (`run-bounded-pipeline.sh` in `record-actual` mode) after the cluster ends.

Upload of a local export to the curated bucket: `scripts/upload-slice.sh --export-dir DIR --run-prefix P --bucket B` (dry run by default). Vector ingest and query smoke are separate human-approved commands described in the live-session runbook (blocks 24 to 26 of the Session 2 plan).

## 7. Common failures

| Symptom | Where it happened | What to do | Record |
|---|---|---|---|
| `terraform` or script refuses with exit 3 | any gate | read the `RESULT: REFUSED step=...` line; the usual causes are a wrong Terraform version, a dirty tree, a stale pre-spend receipt, or an approval record that does not match the plan checksum. Fix the input; do not edit the script | [scripts/README.md](../scripts/README.md), "Exit codes" |
| plan stops on a precondition | stage a plan attempt 1 | Session 1 runtime values were still in the private variables; nothing was applied; correct the variables and plan again | [human-gate](agent-runs/phase-15/human-gate.md), Stage a |
| S3 `RequestTimeout` on the 322 MB archive upload | base-apply 1 | do not re-run the same stage; plan again (expect 0 changes), new record serial, dry run, then base-apply with `s3.max_concurrent_requests` 2 on a wired network | [incident](incidents/2026-11-18-base-apply-runtime-archive-requesttimeout.md) |
| every ingest item rejected with HTTP 401 | ingest 1 | test the key with one request (expect HTTP 200) before ingest, replace the secret value in the console under the recorded decision, then run ingest again under a new run id and approval file | [incident](incidents/2026-11-18-vectors-ingest-1-voyage-401.md) |
| EMR `spark-job` step `FAILED` with "Unknown Error." | Session 2 EMR run | read the step failure JSON and the step log; the cause is a missing `EmrFileSystem` class in the template fetch and is not fixed; use the local P6 export as the fallback | [incident](incidents/2026-11-18-emr-spark-job-step-emrfilesystem.md), [s1-spark-failure.json](agent-runs/phase-15/evidence/session-2/emr/s1-spark-failure.json) |
| 503 and 504 burst under load; the load generator aborts on its 5xx guard | `hold-50` | stop; do not rerun without approval; save service events, alarm history and ALB logs next to the poll before the next live load | [incident](incidents/2026-11-18-rb-load-test-abort-5xx-burst.md) |
| blank lines in a monitor log (credential gaps) | the ECS poll | the role session lasts 1 hour; log in again and renew inside long loops; run an STS caller-identity check before login-sensitive steps | [incident](incidents/2026-11-18-deployer-session-drops.md) |
| `AccessDenied` on a step the kit expects to pass (secret creation, key put, secret deletion) | a7, b3b, c5 | the narrow policies were missing from the kit; add only the reviewed narrow policy under a recorded decision and remove it afterwards; never widen IAM broadly | [incident](incidents/2026-11-18-kit-missing-a7-b3b-c5-policies.md), [permission gaps](incidents/2026-11-18-console-permission-gaps.md) |
| destroy pass 1 `PARTIAL` at `aws_eip.nat` `DisassociateAddress` 403 | cleanup | expected: the deployer role has no `ec2:DisassociateAddress`; do not widen IAM; run the listing again for a fresh token and a second pass | [cleanup-results.txt](agent-runs/phase-15/evidence/session-2/section-c/cleanup-results.txt) |
| `RESULT: REFUSED step=confirm` (exit 3) on the cleanup listing | cleanup listing 1 | by design: review the listed deletes, then pass the token with `--confirm` | same |
| query returns 401 | any route | the bearer token is missing or wrong; internal routes need the internal token, public routes the public key | [docs/api.md](api.md) |
| query returns 202, 429, 502, 504 | runtime | 202 is a job reference; 429 `THROTTLED` is terminal for that key (use a new key); 502 and 504 are retried inside the workflow; see the typed-error table | [docs/api.md](api.md), "Typed errors" |
| local `hadoop` tests fail with `getSubject` | local build | the default JDK is newer than 17; run with JDK 17 | scripts README, Prerequisites |

If a failure is not in this table, record it before changing anything (section 8).

## 8. Incident escalation

1. Stop the step. Do not retry, roll back or clean up on your own judgment unless the scripts README names that action for the stage.
2. Save the log of the failing step and note the `STEP:` and `RESULT:` lines. Redact account ids, host names and keys before sharing ([Session 2 INDEX](agent-runs/phase-15/evidence/session-2/INDEX.md), Redaction).
3. Tell the coordinator the log path and the marker lines. The coordinator routes diagnosis to the incident-responder, whose records are written under `docs/incidents/` ([docs/agents.md](agents.md)); the incident-responder may do only approved, bounded recovery.
4. The human decides anything with live risk: a retry of an apply, a rollback, an IAM change, a scale change or data destruction. The decision is written into the phase evidence before the action.
5. After recovery, add the record with timeline, impact, root cause (or "not determined"), recovery decision and follow-ups. The format is in [docs/incidents/README.md](incidents/README.md); the worked example for a gate that stopped safely is [the P0 budget incident](incidents/2026-11-16-p0-budget-modify-backup-check.md).

Cost escalation: the project ceiling is USD 25 and budget alerts fire at USD 18, 20 and 22 ([service limits](service-limits.md), section 5). Read the AWS, Anthropic and Voyage consoles and render the combined report with `python3 -I scripts/lib/cost_report.py render --input <file>`; the Session 2 report is [cost-report.log](agent-runs/phase-15/evidence/session-2/c11/cost-report.log).

## 9. Rollback

Rollback is a deployment: it needs a new approval record, a fresh pre-spend receipt and a plan receipt. There is no console shortcut and no data repair ([scripts/README.md](../scripts/README.md), "Rollback behavior (policy 13-5)").

- **Application rollback** to the previous images: `scripts/rollback.sh --env E --region R --previous-manifest <deploy-manifest.json>`. The script checks the previous manifest holds digests for all four services and that each registry tag still resolves to its recorded digest; `--stage plan` re-plans with `--image-revision <previous commit SHA>`; after review and a new approval record, `--stage deploy --plan <PLAN-FILE>` runs `deploy.sh --stage runtime-apply --reuse-images`, which pushes nothing and verifies the four task definitions.
- **Infrastructure rollback**: `scripts/rollback.sh --mode infra --previous-commit SHA` runs the current scripts against the Terraform source as committed at that SHA. While the live state shows a deployed runtime, the rollback keeps it by carrying the deployed image revision; while it does not, a rollback bound to a push record is refused.
- Image tags are immutable in ECR, so a tag cannot be overwritten; roll back by selecting the older digest, never by re-pushing a tag.

Replay status: the dry-run paths and their tests exist offline (`scripts/tests/test_rollback.py` and related suites, which run inside the script-tests gate of `scripts/check.sh`; not run separately in 17A or 17G); `rollback.sh --help` was replayed in 17A (exit 0). No rollback was executed on AWS in either live session: no rollback line appears in the Session 2 decision log (searched). Rollback is therefore documented and tested offline only; the live path is unverified. Not replayed in 17G either.

## 10. Cleanup

Policy for the course session: a full purge after evidence is archived and downloads are taken; preserved are only the Terraform state backend settings and S3 objects the main root does not manage ([scripts/README.md](../scripts/README.md), "Cleanup behavior and preservation policy"). Order, as run in Session 2 (blocks 36 to 40 and Section C of the decision log):

1. **Archive evidence first.** `scripts/archive-evidence.sh --phase NN --label L --include CATEGORY=PATH` writes a new evidence folder with an index; download reports from S3 before destruction. (Session 2: archive PASS at 21:48 UTC; the EMR copy-out never ran, so no pipeline output was downloaded.)
2. **Prepare.** `scripts/cleanup.sh --env E --region R --prepare [--image-revision <deployed revision>] --execute` plans the release of deletion protection (Neptune, load balancer, DynamoDB, ECR, S3, S3 Vectors). Apply exactly that plan with `scripts/deploy.sh --stage cleanup-prepare --plan <PLAN-FILE> ... --execute` under a new approval record. Session 2: 20 updates, plan passed.
3. **Listing, then confirmed destroy.** `scripts/cleanup.sh --env E --region R --execute` lists the destructive actions and refuses with exit 3 by design; review the list; then `--confirm TOKEN --plan <DESTROY-PLAN-FILE>`. The token is bound to the saved plan, the live account hash, region and environment. Session 2: listing 1 showed 201 deletes; pass 1 destroyed down to 65 inventory entries and stopped `PARTIAL` at the EIP 403; pass 2 removed the last item (65 to 63).
4. **Remove operator roles** with the deployer apply that turns them off (Session 2, step C4: 13 destroyed), then the deployer role itself later by the reviewed P39 procedure (2026-11-19: 18 destroyed, role gone).
5. **Delete the four secrets** (force delete) and **revoke both provider keys** in the provider consoles (Session 2: secrets deleted, Voyage keys revoked at 22:46 UTC).
6. **Check, read-only.** KMS key pending deletion, tagging-API inventory, S3 buckets gone, no EIP, NAT, load balancer or Neptune left (console checks by the human). Session 2: 63 inventory entries remained, which the human gate describes as two free guards plus tagging-index entries judged to be leftovers of deleted or inactive resources; the state of the second KMS key in the inventory was not read ([human-gate.md](agent-runs/phase-15/human-gate.md); [after-cleanup inventory](agent-runs/phase-15/evidence/session-2/inventories/after-cleanup-inventory.txt)).
7. **Read the bills.** Cost Explorer by service for the days after cleanup, and the Anthropic and Voyage consoles. Session 2: no resource still accruing on 2026-11-19 and 2026-11-20 at the reading time (AWS total USD 17.88 for 2026-11-01 to 2026-11-20).

Rehearsal status: the destroy sequence was executed live in Sessions 1 and 2 ([Session 1: 309 to 62 to 60 entries](agent-runs/phase-14/human-gate.md); [Session 2](agent-runs/phase-15/evidence/session-2/section-c/cleanup-results.txt)); the script logic is tested offline in `scripts/tests/test_cleanup.py` (inside the script-tests gate of `scripts/check.sh`; not run separately in 17A or 17G). A new rehearsal needs a live stack and a human gate and was not done in package 17A or 17G.

## 11. Where to find things after a run

| Need | Path |
|---|---|
| Timeline of record of a live session | `docs/agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md` |
| Evidence index with sha256 per file | `docs/agent-runs/phase-15/evidence/session-2/INDEX.md` |
| Phase results and human acceptance | `docs/agent-runs/phase-15/human-gate.md`, `docs/agent-runs/phase-16/human-gate.md` |
| Frozen evaluation results | `experiments/results/phase16/` and [docs/report/evaluation.md](report/evaluation.md) |
| Experiment manifests and approvals | `experiments/manifests/`, [experiments/README.md](../experiments/README.md) |

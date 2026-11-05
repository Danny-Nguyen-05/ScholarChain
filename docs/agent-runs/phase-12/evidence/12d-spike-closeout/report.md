# Phase 12D closeout report — EMR Spark feasibility spike

STATUS: COMPLETE. One runtime is proven with evidence: candidate (a) of the 12D plan, EMR on EC2 with a bootstrap-installed Spark 3.5.4 / Scala 2.13 runtime. All spike resources are destroyed and inventoried. The 12-10 decision is recorded in [decision-12-10.md](decision-12-10.md). Step D is awaiting the human's independent review and the Phase 12 human gate.
OWNER: coordinator. The coordinator assembled this closeout from the Step A to C evidence. No specialist subagent was launched in Step D. The Step A and C subagents (build-engineer, infra-engineer, test-engineer, deploy-engineer) all ran on Sonnet 5.5 at high effort, as recorded in `../12d-spike-offline/gates.json` (`subagents`) and `../12d-spike-live/work-order.md`.
WORK ORDER: the plan's Subphase 12D section (`../../prompt.md`, "Subphase 12D — Timeboxed EMR Spark feasibility spike"). The Step A work order is [../12d-spike-offline/work-order.md](../12d-spike-offline/work-order.md), and the Step C work order is [../12d-spike-live/work-order.md](../12d-spike-live/work-order.md). Live authority is [../12d-spike-live/human-approval.md](../12d-spike-live/human-approval.md) with Amendments 1 to 4.
FILES CREATED: this folder (`report.md`, `decision-12-10.md`, `carried-findings.md`, `human-gate-handoff.md`, `evidence-manifest.json`).
FILES MODIFIED: append-only pointer sections in `../../owner-report.md`, `../../test-report.md`, `../../repairs.md` and `../../review.md`. No source, infrastructure, script, test or human-owned file was changed in Step D.
COMMANDS RUN (Step D): reads of the repository and evidence only; a scan of the evidence for 12-digit numbers; `sha256sum` for the manifest. No AWS call, login, credential or state read, plan, apply or destroy was made.
TEST RESULTS: none were re-run in Step D. The last observed gates were at source commit `2d38f0f`, before attempt 5:
- deployer mock tests 29/29;
- spike mock tests 38/38;
- script tests 70 OK;
- source guard 0 findings;
- `sbt check` attempt 10 exit 0, 1,267 succeeded and 0 failed (`../12d-spike-offline/gates.json`).
VALIDATION RESULTS: the live result is the 12D verification table below.
ASSUMPTIONS: cost is modeled, not billed. The Billing reconciliation is still pending.
RISKS: see "Proven scope and limits" below and [carried-findings.md](carried-findings.md).
MANUAL ACTION REQUIRED: see [human-gate-handoff.md](human-gate-handoff.md).
BLOCKED-ON OWNER: none for 12D.
BLOCKED-ON EVIDENCE: none for 12D.
NEXT GATE: the human's independent review of Step D, then the human writes `human-gate.md` and `commit.txt` for Phase 12.

## The question and the answer

**Question (plan, 12D goal):** can the existing Phase 6 Spark job run the G1 fixture on a real Spark cluster on AWS, with Scala 2.13 libraries on both the driver and the executors?

**Answer: yes.** Attempt 5 ran on 2026-11-04 on cluster `j-…153M668H5I3`, using EMR 7.8.0 with 1 primary and 1 core m5.xlarge in us-east-2a. The run was at source commit `2d38f0f`, and the evidence was committed in `2d2d224`. Details are in [../12d-spike-live/attempt5-success.md](../12d-spike-live/attempt5-success.md), and the redacted proof files are in [../12d-spike-live/attempt5-proof/](../12d-spike-live/attempt5-proof/).

| 12D task 2 check | Evidence | Result |
|---|---|---|
| The job completes | probe, g1 and collect steps all `COMPLETED`; the cluster ended `TERMINATED` with `ALL_STEPS_COMPLETED` | ✅ |
| The driver and executor class origins are Scala 2.13, not 2.12 | The driver JVM and a separate executor JVM both load `scala-library-2.13.14.jar`, `scala-reflect-2.13.14.jar` and `spark-core_2.13-3.5.4.jar`. `-Xlog:class+load` shows 6 container JVMs, 18 matches and **0 files mentioning 2.12**. The coordinator re-derived these counts. | ✅ |
| DataFrame and Parquet read and write work | G1 reads its JSON inputs and writes 28 Parquet tables through DataFrame `.parquet(...)`; the comparison read all 28 back | ✅ |
| The output tables equal the local run's rows | `allExactRowsMatch=true` with 28/28 tables, each `exactSchemaAndRowsMatch=true`, 587 rows in total and `provenanceNormalization: none`. The run used the same `runId run:2047866e-…`, code version and upstream manifest hashes as the local baseline. The coordinator re-checked this. | ✅ |

| 12D task 3 | Result |
|---|---|
| Cost | Modeled across all five attempts: about **USD 0.35**, plus up to USD 5 if each of the 5 KMS keys is counted as a full month. That is about **USD 5.35, under the USD 10 cap**. Not yet reconciled in Billing. |
| Elapsed time | The successful cluster ran 11 min 5 s. The live day ran from 11:19 to about 15:55 CST, including four repair and review cycles. The 2026-11-06 timebox was met. |
| Destroy and after-inventory | Spike state is empty. `inventory.sh` returned `clean: true`, with no billable resources left. The 5 KMS keys are in PendingDeletion (7-day window) and are the only expected leftover. The tagging API still lists security-group-rule and VPC-endpoint ARNs, but direct describes find none of them. |

Candidate (b), EMR Serverless, was not tested. It was ruled out by the human's decision, and the plan's "stop at the first that works" rule did not require it. Task 4, the fallback options, was not triggered.

## Attempt history (all destroyed and inventoried clean)

| # | Outcome | Root cause | Fix (reviewed before the next attempt) |
|---|---|---|---|
| 1 | Partial apply, no cluster | Create calls were denied on existing stack parents (the VPC and others), and credential refresh expired | `Ec2CreateOnExistingStackParents`, the L1 access-point fix and the `credential_process` profile (commit `7963b87`) |
| 2 | Cluster failed validation | The boundary denied `ec2:RunInstances` on the AMI (found in CloudTrail) | `V2ExistingLaunchDependencies` (`35e868a`) |
| 3 | Instances launched, bootstrap exited 4 | The hard-coded Java path is absent on EMR 7.8.0 | Java 17 is resolved at run time (`bf685ff`) |
| 4 | Runtime proven, G1 failed | EMR's `io.compression.codecs` names LZO, which the runtime does not ship | Codec override in the Spark defaults (`2d38f0f`) |
| 5 | **Success** | — | — |

Each retry was authorized separately by the human (Amendments 1 to 4). The human ran every apply and destroy in their own terminal, because Claude Code's permission classifier blocks agent apply and destroy. The deploy-engineer ran the plan, the plan-rule check, monitoring, collection, comparison and inventory.

## Proven scope and limits

These are proven live: a 1+1 m5.xlarge cluster; YARN cluster mode; 2 static executors (no dynamic allocation, no shuffle service); the G1 fixture; `file:///` on EFS shared by both nodes; Spark authentication with AES-CTR network crypto (`authEngineVersion=1`) and IO encryption; Hadoop-only EMR applications.

**Termination: only two paths were observed live.**
- *Steps-then-terminate* (`keep_job_flow_alive_when_no_steps=false`): the cluster terminated by itself after its last step, in attempt 4 (where G1 failed and collect completed) and in attempt 5 (where all steps completed).
- *Node shutdown timer arming*: in attempt 3 the bootstrap armed the timer first, at 114 min.

These layers were **not observed**:
- the shutdown timer expiring;
- the 900 s idle auto-termination;
- `TERMINATE_CLUSTER` firing on a collect-step failure, because collect never failed.

The approved limitation stands: the node shutdown timer is best effort. The guarantees relied on are steps-then-terminate, `TERMINATE_CLUSTER` on collect, the 900 s idle timeout and the same-session destroy (`../12d-spike-live/human-approval.md`, "Accepted residual risks"). Of these, only steps-then-terminate and the destroy were exercised.

These are **not** proven by this spike and are carried into [decision-12-10.md](decision-12-10.md):
- S3 input and output from the custom runtime;
- EMR in-transit TLS (the main module's security configuration) together with the custom runtime;
- task nodes, managed scaling and dynamic allocation;
- data larger than G1;
- AES-GCM (a disclosed limitation);
- encryption of Hadoop and YARN RPC.

## Defects and deviations disclosed

- `collect-evidence.sh` exited 1 on macOS in attempt 5. The results were verified with Python `tarfile` instead: 241/241 files matched. This is carried as item 31.
- Every destroy from attempts 2 to 5 needed a second pass, because of the `aws_eip.nat` `DisassociateAddress` 403 on `*/*`. This is carried as item 24.
- Manual IAM windows outside Terraform used root in the console only, with `IAMFullAccess` added and then removed, three times. They are documented in human-approval.md. The human should confirm the close times in CloudTrail.
- Reviews were recorded in `../12d-spike-offline/review-findings.md`, the lean format the human chose, rather than verbatim in `review.md`. `review.md` gets a pointer section.

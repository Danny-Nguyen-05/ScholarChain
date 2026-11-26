# Incident 2026-11-25: EMR hadoop-prep step failed, job 2 input path (job 1 output) not found on the shared mount

Status: mitigated by one retry (run 5 passed all six steps on the same cluster); root cause open. Severity: low (bounded spend, no data loss, no unintended cloud change; one of the five allowed EMR runs was used).
Owner: incident-responder (record). Human decisions are quoted from the coordinator's decision log; this record does not alter them.
Sources and limits: written offline from the coordinator's decision log (`../agent-runs/phase-18/evidence/day2/00-timeline/decision-log.md`) and the masked run logs under `../agent-runs/phase-18/evidence/day2/`. Times are UTC on 2026-11-25, with America/Chicago (CST, UTC-6) in brackets where useful. Facts marked "decision log" were recorded live by the coordinator; the responder did not observe them and made no cloud call. The human downloaded the step stderr and pasted it in chat (chat; not in the decision log); the coordinator read the pasted text and wrote the diagnosis (decision log, 11:39 CST entry, which records only the masked exception and the diagnosis). The step stderr is a private copy that this record did not read; only the masked form below is quoted.

## Summary

Day 2 was the live proof of the Phase 18 `sc-step.sh` fix on EMR size S (cluster `j-05116692OZ06APLO3FMD`, us-east-2). The first S attempt (EMR run 4 of 5 allowed, run id `15a-emr-size-100-20261125T173348Z-95764`) failed at its second step, `hadoop-prep` (step `s-0953120XL3EAP77LXI2`). The step ran 17:34:40Z-17:35:59Z [11:34:40-11:35:59 CST]. The pipeline reported `STEP-RESULT: hadoop-prep ... FAILED`, then `RESULT: FAIL step=step-hadoop-prep`, and exited 4. The stage-in step before it had completed.

Masked step stderr (decision log):

`InvalidInputException: Input path does not exist: file:/mnt/scholarchain/runs/<run>/hadoop/<id>/intermediate/j02` at `PrepJobs.run`.

Job 2 reads job 1's output as its input, on the shared `/mnt/scholarchain` mount. That path was not visible where job 2 ran. This is not the Phase 18 `spark-job` path: the failure came before the `spark-job` step and in different code. The human chose "Retry now" at about 17:40Z. The retry (run 5, `15a-emr-size-100-20261125T174034Z-99560`) passed all six steps on the same cluster.

## Timeline

| Time (UTC) [CST] | Event | Source |
|---|---|---|
| 17:32:09 [11:32:09] | EMR-enable deploy ended PASS; cluster created inside 17:26-17:32Z | decision log (11:32 CST entry) |
| 17:33:52 | Ledger reserved for run 4 (id stamp `20261125T173348Z`); live_runs 4 of 5 | `../agent-runs/phase-18/evidence/day2/emr/emr-run-1.log` |
| 17:34:24 | hadoop-prep pre-spend receipt re-verified; step submitted (`s-0953120XL3EAP77LXI2`) | `emr-run-1.log` |
| 17:34:40-17:35:59 | hadoop-prep step window | decision log (11:39 CST entry) |
| 17:36:29 | `ERROR failed at step step-hadoop-prep ... state FAILED`; `RESULT: FAIL step=step-hadoop-prep`; pipeline exit 4 | `emr-run-1.log` |
| 17:37:02 | `record-actual`: measured USD 0.09, tail USD 0.14; ledger live_runs 4 of 5, cumulative USD 2.28, cap 4.70 | `../agent-runs/phase-18/evidence/day2/emr/emr-actual-1.log` |
| about 17:39 [11:39] | Diagnosis by the coordinator from the stderr text the human pasted in chat; hypothesis: intermittent shared-mount visibility | decision log (11:39 CST entry) |
| 17:40 [11:40] | Human decision, verbatim: "Retry now" (S retry, run 5, last allowed, same cluster, USD 1.25 cap, 120 min) | decision log (11:40 CST entry) |
| 17:40:34-18:14:39 | Run 5 `15a-emr-size-100-20261125T174034Z-99560`: all six steps COMPLETED; pipeline `RESULT: PASS` | decision log (12:18 CST entry); `../agent-runs/phase-18/evidence/day2/emr/emr-run-2.log` |

## Detection

The pipeline script printed `STEP-RESULT: hadoop-prep s-0953120XL3EAP77LXI2 FAILED` and exited 4 (`emr-run-1.log`). The human downloaded the step stderr and pasted it in chat; the coordinator read the pasted text for the exception text.

## Impact

- One of the five allowed EMR runs was used (the cap was raised from 4 to 5 for Day 2). The ledger is now 5 of 5 runs, cumulative USD 2.65 of the 4.70 cap (`emr-actual-2end.log`). No further EMR run is possible without a new human decision.
- Cost of run 4, as ledger estimates (0.555 USD per hour times the window, not billed cost): USD 0.09 for the window 17:27:42Z-17:37:02Z, plus a USD 0.14 idle tail at record time (`../agent-runs/phase-18/evidence/day2/emr/emr-actual-1.log`, line 4). Run 5's ledger window starts where run 4's ends (17:37:02Z-18:19:31Z, `emr-actual-2.log`, line 4). The idle tail went to 0 in the record after the cluster terminated at 18:32:05Z (`emr-actual-2end.log`). The decision log gives Day 2 EMR as USD 0.60 (run 4 0.09 plus run 5 0.51), also an estimate.
- Time: about 3 minutes for the failed attempt (17:33:48Z to the 17:36:29Z failure line), then the retry.
- No data loss. No Phase 18 result depends on run 4; the proof of the fix is run 5.

## Root cause

Proximate cause (decision log, masked stderr): job 2 of `PrepJobs.run` could not find its input directory `.../intermediate/j02` under `file:/mnt/scholarchain/runs/<run>/hadoop/<id>/`. Job 2's input is job 1's output.

Underlying cause: not determined. Hypothesis only, not verified: intermittent visibility of the shared mount (EFS) between the node that wrote job 1's output and the node that ran job 2, or a mismatch between a local path and a shared path in how the job resolves `file:/mnt/...`. No root-cause run was made. Known: the jar and config hashes match Session 2 (2026-11-18), and Session 2 passed `hadoop-prep`. `scripts/emr/sc-step.sh` did change in package 18A (sha256 `1edcf68d29481015da5675aad7fbe74d4af685f9d0c27a5378f23ffeab7c8eed`), but `git diff v1.0-final..HEAD -- scripts/emr/sc-step.sh` has only two hunks, starting at old lines 328 (end of `body_spark_class_origin`) and 341 (`body_spark_job`); `body_hadoop_prep` (`scripts/emr/sc-step.sh:270`) is unchanged. The retry on the same cluster also passed. Those two facts fit an intermittent cause and do not rule out a race that appears only sometimes. Not recorded: which node ran each job, how long the gap was between job 1's write and job 2's read, and whether EFS was the mount in both cases.

## Trace and run IDs

- Failed run: `15a-emr-size-100-20261125T173348Z-95764`; step `s-0953120XL3EAP77LXI2`; cluster `j-05116692OZ06APLO3FMD`.
- Retry run: `15a-emr-size-100-20261125T174034Z-99560`; its hadoop-prep step `s-0954148V87F5C0OSC6C` COMPLETED.
- HEAD `fe0b6cc` (the committed Phase 18 state).

## Recovery and the human decision behind it

The coordinator recorded the failure, noted that the retry cost condition was met (retry admitted at the 3.53 reservation level), and asked the human. The human answered "Retry now" (decision log, 11:40 CST). The retry was the last allowed run. It passed, so the Phase 18 fix was proven on EMR in run 5. The decision log shows no repair or change of code between the two runs.

## What was not done

- No root-cause run and no read of job 1's output location after the failure.
- No change to `PrepJobs`, the mount or the cluster between the two runs.
- No committed copy of the step stderr; the private copy stays outside the repository.

## Follow-ups

Proposals for the owners; none is decided.

| Item | Owner | Status |
|---|---|---|
| Check offline whether `PrepJobs` job 2 reads job 1's output through the shared `/mnt/scholarchain` mount, and whether a sync or visibility check before job 2, or an HDFS intermediate, would remove the race | hadoop-engineer | Proposed |
| If a live check is wanted later, it needs a new human decision (the EMR ledger has no run left) | human architect | Not requested |

## Evidence

- `../agent-runs/phase-18/evidence/day2/00-timeline/decision-log.md` (11:32, 11:39, 11:40, 12:18, 12:19 and 12:33 CST entries)
- `../agent-runs/phase-18/evidence/day2/emr/emr-run-1.log` (masked)
- `../agent-runs/phase-18/evidence/day2/emr/emr-run-2.log` (masked)
- `../agent-runs/phase-18/evidence/day2/emr/emr-actual-1.log`, `../agent-runs/phase-18/evidence/day2/emr/emr-actual-2.log`, `../agent-runs/phase-18/evidence/day2/emr/emr-actual-2end.log`
- Related record: `2026-11-18-emr-spark-job-step-emrfilesystem.md` (the Phase 18 `spark-job` fix, resolved in run 5)

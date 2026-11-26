# Incident 2026-11-18: EMR spark-job step failed in its template fetch (EmrFileSystem ClassNotFoundException)

Status: open as a known limitation (accepted by the human on 2026-11-20; root cause not determined, no fix made). Severity: medium (the EMR Spark path was not proven; bounded spend, no data loss).
Owner: incident-responder (record). Fix owners named in the Phase 15 closeout: spark-engineer and infra-engineer, after the session, not on the frozen commit.
Sources and limits: written offline from the committed Session 2 evidence. Times are UTC on 2026-11-18, with America/Chicago (CST, UTC-6) in brackets where useful. Facts marked "decision log" were recorded live by the coordinator; the responder did not observe them and made no cloud call. The step stderr that shows the exception text is a private, git-ignored copy that this record did not read; the exception text is taken from the decision log and `../agent-runs/phase-15/human-gate.md`. Human decisions are quoted from the decision log and are not altered here.

## Summary

In the Session 2 EMR run `15a-emr-size-100-20261118T163203Z-87466` (cluster `j-00663481CVHVEQEYZQ5L`, size-100 input), the stage-in, Hadoop-prep, entity-resolution and spark-class-origin steps completed. The next step, `spark-job` (step `s-09595101MXOLD79N7UTQ`), failed about 32 s after submission. The coordinator's diagnosis of the step stderr: the step's template fetch, `hadoop fs -copyToLocal`, raised `ClassNotFoundException com.amazon.ws.emr.hadoop.fs.EmrFileSystem` and exited 255, so Spark never started. EMR reported only `Reason: "Unknown Error."` The coordinator classed it as a deterministic configuration error and chose no retry. The human agreed and used the step 7b fallback: the local P6 S export `run:ba7402d1-959a-4277-8c6e-e92878a38afa` on the same HEAD.

## Timeline

| Time (UTC) [CST] | Event | Source |
|---|---|---|
| 16:26:54 [10:26:54] | EMR billing window starts (ledger actual window) | `../agent-runs/phase-15/evidence/session-2/emr/emr-actual-1.log` |
| 16:30:54 [10:30:54] | EMR enable deploy PASS, cluster booting | decision log line 30 |
| 16:32:03 [10:32:03] | `run-experiment.sh` starts the run, delegates to `run-bounded-pipeline.sh` | `../agent-runs/phase-15/evidence/session-2/emr/emr-run-1.log` |
| 16:32:40-16:40:50 | hadoop-prep step (submission instants) | `../agent-runs/phase-15/evidence/session-2/emr/emr-run-1.log`; decision log line 31 |
| 16:40:50-16:46:58 | entity-resolution step | same |
| 16:46:58 | spark-class-origin submitted; COMPLETED | `../agent-runs/phase-15/evidence/session-2/emr/emr-run-1.log` |
| 16:48:00 [10:48:00] | `spark-job` submitted (`s-09595101MXOLD79N7UTQ`) | `../agent-runs/phase-15/evidence/session-2/emr/emr-run-1.log` |
| 16:48:32 [10:48:32] | `STEP-RESULT: spark-job ... FAILED`; pipeline `RESULT: FAIL step=step-spark-job`, exit 4 (reported by `run-experiment.sh` as `run-bounded-pipeline.sh exited 4`) | `../agent-runs/phase-15/evidence/session-2/emr/emr-run-1.log` |
| 16:56:18 | `record-actual`: measured 0.28 plus tail 0.14 (reserved 0.84); ledger live_runs 3 of 4, cumulative USD 2.10, cap 3.53; retry cost condition (at most 0.87) met | `../agent-runs/phase-15/evidence/session-2/emr/emr-actual-1.log`; decision log line 32 |
| 16:58:56 [10:58:56] | Diagnosis from the step stderr (private copy); coordinator decision: no retry; record 2 prepared but not submitted, ledger slot unused; cluster left to idle-terminate; go to block 22 (step 7b fallback) | decision log line 33 |
| 17:00:30 [11:00:30] | Human decision (chat), verbatim: "agree: no S retry (deterministic EmrFileSystem error); use step 7b local S export". Block 22 PASS: P6 S export `run:ba7402d1-959a-4277-8c6e-e92878a38afa`, SHA256SUMS check 0 failures, provenance head equals HEAD `bd0b818` | decision log lines 34-35 |
| 17:02:08 | Cluster still WAITING (idle 900 s from 16:48:32; auto-termination policy 900) | decision log line 36 |
| 17:06:31 [11:06:31] | Cluster end time; TERMINATED recorded in the decision log at 17:42:17 | `../agent-runs/phase-15/evidence/session-2/emr/emr-actual-1end.log`; decision log line 39 |

## Detection

The pipeline script reported `STEP-RESULT: spark-job s-09595101MXOLD79N7UTQ FAILED` at 16:48:32Z and exited 4. The EMR step record carries only `Reason: "Unknown Error."` and a log location (`../agent-runs/phase-15/evidence/session-2/emr/s1-spark-failure.json`; the bucket name in it is redacted). The exception text was found by the coordinator in the downloaded step stderr.

## Impact

- Spark on EMR was not proven in Session 2. The vectors and the graph used later came from the local P6 S export on the same HEAD, not from EMR output (`../agent-runs/phase-15/human-gate.md`, "EMR Spark on EMR not proven").
- Cost: the EMR part of Session 2 was USD 0.37 (2,377 s at 0.555 per hour, tail 0); ledger 3 of 4 runs, cumulative USD 2.05 of 3.53 (`../agent-runs/phase-15/evidence/session-2/emr/emr-actual-1end.log`, decision log line 39). One ledger slot remains.
- The Phase 16 evaluation has no EMR Spark runtime: `experiments/results/phase16/performance/performance-metrics.md` section 5 and the GAP list state that only this size-100 run reached the Spark step and failed.
- Hadoop counters from the same run were still captured: INPUT 290,343, ACCEPTED 515,309, REJECTED 1,243 (`../agent-runs/phase-15/evidence/session-2/emr/hadoop-prep-counters.txt`); `../../experiments/results/phase16/performance/performance-metrics.md` section 5 reports the counters identical on EMR and local.
- Unaffected: the render, ingest and query-smoke steps, which used the fallback export.

## Root cause

Proximate cause (decision log, from step stderr, not independently re-read here): `hadoop fs -copyToLocal` in the `sc-step` template fetch could not load `com.amazon.ws.emr.hadoop.fs.EmrFileSystem`; exit 255; Spark never started.

Underlying cause: not determined. Known: the four earlier steps on the same cluster completed, and the coordinator judged the error deterministic, not transient. Not recorded: why the class was missing for this step, whether it was the same fetch path other steps used, and the cause of the "Unknown Error." wording. The decision log says the root cause is "to be fixed after the session (spark-engineer/infra-engineer), not on the frozen commit"; no later diagnosis is recorded in the evidence read.

## Trace and run IDs

- Experiment run: `15a-emr-size-100-20261118T163203Z-87466`; script run ids `20261118T163203Z-87466` (run-experiment) and `20261118T163204Z-87595` (pipeline).
- Cluster `j-00663481CVHVEQEYZQ5L`; failed step `s-09595101MXOLD79N7UTQ`; spark-class-origin step `s-09814723LU3FPZ2QVXB3`; entity-resolution step `s-0810437381KJNWGMEWYW`.
- Committed manifest `experiments/manifests/15a-emr-size-100.json` at HEAD `bd0b8180b919ed61f6234fa515f4c07d1137a641`.
- Fallback export: `run:ba7402d1-959a-4277-8c6e-e92878a38afa`.

## Recovery and the human decision behind it

No retry. The human's decision of 2026-11-18T17:00:30Z (quoted above) confirmed the coordinator's recommendation and the step 7b fallback that the human had approved earlier in the plan (`docs/runbooks/session-2-plan.md`, section 5.2 step 7b). The cluster was left to idle-terminate under the 900 s policy. The human's acceptance decision of 2026-11-20 lists the EMR Spark step as a known limitation, "fix only if time allows".

## What was not done

- No retry of the spark-job step and no submission of the prepared second record.
- No fix on the frozen commit; no diagnosis beyond the step stderr.
- No EMR output was copied out (`copy-out` never ran; decision log line 69).
- No EMR Spark runtime was measured.

## Follow-ups

| Item | Owner | Status |
|---|---|---|
| Find why the `EmrFileSystem` class is missing in the spark-job step's `copyToLocal` and fix it | spark-engineer / infra-engineer | Open; fix only if time allows (human, 2026-11-20); the fourth ledger slot would be needed for any live proof |
| Save the step stderr text, or a redacted excerpt, as committed evidence | documentation-engineer (assembly) | Not recorded as done; the private copy stays outside the repository |

## Evidence

- `../agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md` (lines 30-36, 39, 69)
- `../agent-runs/phase-15/evidence/session-2/emr/emr-run-1.log`
- `../agent-runs/phase-15/evidence/session-2/emr/s1-spark-failure.json`
- `../agent-runs/phase-15/evidence/session-2/emr/emr-actual-1.log`
- `../agent-runs/phase-15/evidence/session-2/emr/emr-actual-1end.log`
- `../agent-runs/phase-15/evidence/session-2/emr/cluster-id.log` and `../agent-runs/phase-15/evidence/session-2/emr/cluster-final-state.log`
- `../agent-runs/phase-15/evidence/session-2/emr/hadoop-prep-counters.txt`
- `../agent-runs/phase-15/human-gate.md` (Session results, open items)
- `../../experiments/results/phase16/performance/performance-metrics.md` (sections 5 and 9)
- `../runbooks/session-2-plan.md`

## Resolution update (2026-11-25)

Status: resolved (fix verified on EMR, one run). This status supersedes the Status line at the top of the record. The text above is the record as written on 2026-11-18 to 2026-11-20 and is not changed.

- Fix: Phase 18 package 18A changed `scripts/emr/sc-step.sh` so that the EMR `spark-job` template fetch runs before the portable-runtime environment (`spark_env`) is set. The fixed file has sha256 `1edcf68d29481015da5675aad7fbe74d4af685f9d0c27a5378f23ffeab7c8eed` and is committed on branch `phase-18` (HEAD `fe0b6cc` on Day 2). The same hash was seen as the installed step runner in the Day 2 EMR config write and upload checks (decision log, 11:23 CST entry).
- Live proof: on Day 2 (2026-11-25), EMR size S, cluster `j-05116692OZ06APLO3FMD`, run 5 `15a-emr-size-100-20261125T174034Z-99560` (17:40:34Z-18:14:39Z) completed all six steps. The `spark-job` step `s-08041352ORZOW9X35U3M` COMPLETED. Run 5 was a retry of run 4, which had failed earlier at `hadoop-prep` for an unrelated reason (see `2026-11-25-emr-hadoop-prep-intermediate-missing.md`).
- Output: export `spark/run:30b3ef84-11dc-4c8c-b9c2-c632477d7282`, with the `_SCHOLARCHAIN_SPARK_COMPLETE` marker. Counters: canonicalWorks 10578, canonicalResearchers 21819, allYearsEdges 81181, components 3942.
- Step durations in run 5: hadoop-prep 7m6s, entity-resolution 6m2s, spark-job 16m38s (source: EMR console Steps tab, human screenshot during the session; clip `p18-clip1-emr-steps-2026-11-25.mov`, hash in `../agent-runs/phase-18/evidence/day2/recordings/clips.txt`).
- Limits: one live run only. No separate root-cause run was made; the fix is inferred from the ordering change (template fetch before `spark_env`) and verified by the passing step, not by a reproduction of the 2026-11-18 error. The first Phase 15 follow-up row above (find and fix the missing class) is met by this fix; the stderr-evidence row is unchanged.
- Sources: `../agent-runs/phase-18/evidence/day2/00-timeline/decision-log.md` (11:23, 12:18 and 12:20 CST entries) and `../agent-runs/phase-18/evidence/day2/emr/emr-run-2.log` (masked). The sc-step.sh sha256 equals `shasum` of the committed `scripts/emr/sc-step.sh` and the pin in `infra/terraform/emr-step-programs.json:7` (confirmed by the coordinator). The step durations are from the EMR console Steps tab, human screenshot during the session; clip `p18-clip1-emr-steps-2026-11-25.mov` (hash in `../agent-runs/phase-18/evidence/day2/recordings/clips.txt`).

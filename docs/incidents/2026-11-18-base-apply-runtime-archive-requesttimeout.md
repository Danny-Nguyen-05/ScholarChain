# Incident 2026-11-18: base-apply 1 stopped at the runtime-archive upload (S3 RequestTimeout, exit 5)

Status: closed (recovered in session by base-apply 2). Severity: low (about 1 hour of delay; Terraform had already applied cleanly; no data lost).
Owner: incident-responder (record). Human decisions are in the decision log and `../agent-runs/phase-15/human-gate.md`; this record does not alter them.
Sources and limits: written offline from the committed Session 2 evidence; no cloud call. Times are UTC on 2026-11-18, with America/Chicago (CST, UTC-6) in brackets where useful. The full deploy logs are private; the committed excerpt is `../agent-runs/phase-15/evidence/session-2/stage-a/stagea-results.txt`. The decision log lists the 15:07:54Z and 15:08:39Z entries in the order shown below; the order is as recorded.

## Summary

Stage a, block 13: `deploy.sh base-apply --execute` (run `20261118T145040Z-74189`). Its `terraform-apply` step completed (outputs printed), then its `runtime-archive-upload` step failed at 15:04:21Z: `aws s3 cp` of the 321,876,735-byte runtime archive hit `RequestTimeout` on `UploadPart` ("reached max retries: 2", socket idle timeout). The script exited 5 and did not write the deploy manifest. The rule is that a failed mutating run is not re-run. The human chose recovery "A" through the reviewed script: a new plan expected to show 0 changes, a new record serial 2 with the same receipt, a dry run, then `base-apply --execute` again, with `s3.max_concurrent_requests 2` on the deployer-tf CLI profile and a wired, quiet network. Base-apply 2 passed; the upload took about 52 minutes.

## Timeline

| Time (UTC) [CST] | Event | Source |
|---|---|---|
| 14:47:38 [08:47:38] | Stage-a plan PASS (171 creates, IDENTICAL to the reviewed derivation) | decision log line 18 |
| 14:50:16 | Block 13: approval record written (human ran it = approval of base-apply); fresh deployer login about 14:49; dry run PASS (run `20261118T145000Z-73738`); coordinator GO for `--execute` | decision log line 19 |
| 14:50:40 | Base-apply 1 starts (run id `20261118T145040Z-74189`) | run id; decision log line 20 |
| 15:04:21 [09:04:21] | `runtime-archive-upload` FAILED: `RequestTimeout` on `UploadPart`; script exit 5; manifest not written | `../agent-runs/phase-15/evidence/session-2/stage-a/stagea-results.txt`; decision log line 20 |
| 15:06:59 [09:06:59] | Coordinator logs the incident; per rule, not re-run; human decision needed | decision log line 20 |
| 15:07:54 | State backup taken (sha256 prefix 9d4807e9); `s3.max_concurrent_requests 2` set on `scholarchain-deployer-tf` (the human's local CLI config) | decision log line 22 |
| 15:08:39 [09:08:39] | Human decision (chat), verbatim: "A" -- recover the runtime-archive upload through the reviewed script: new plan (expect 0 changes), new record serial 2 (same receipt), dry run, `deploy.sh base-apply --execute`; `s3.max_concurrent_requests 2` on the `deployer-tf` profile; wired/quiet network | decision log line 21 |
| about 15:12 | Fresh deployer login | decision log line 22 |
| 15:12:42-15:13:03 | Recovery plan (run `20261118T151242Z-76267`): PASS, add 0 change 0 destroy 0 replace 0; live state serial 720 (was 548 at the first plan) | `../agent-runs/phase-15/evidence/session-2/stage-a/stagea-results.txt`; decision log line 22 |
| 15:14:09 | Base-apply 2 starts (run `20261118T151409Z-77117`) | run id; decision log line 23 |
| 16:07:24 [10:07:24] | Runtime archive upload verified: size, sha256 metadata, S3 composite checksum (39 parts) | decision log line 23 |
| 16:09:04 [10:09:04] | Base-apply 2 PASS; Terraform step a no-op; manifest `deploy-manifest-base-apply-20261118T151409Z-77117.json` written | decision log line 23 |
| 16:15:29 | Block 14 (ACM validation record) proceeds | decision log line 24 |

## Detection

The deploy script's own output: `RESULT: FAIL step=runtime-archive-upload reason=command failed (exit 1) during the mutating sequence`, with the AWS CLI error text above, and a process exit of 5 as reported by the coordinator. The failure was seen live by the coordinator and the human.

## Impact

- Terraform resources: all created in the same run before the upload step (the committed excerpt shows `terraform-apply` completed; the human-gate summary says Terraform applied all resources). The recovery plan showed no changes, so nothing was missing from the infrastructure side.
- Missing until 16:07:24Z: the runtime archive in the artifacts bucket and the deploy manifest.
- Time: about 1 hour 5 minutes (1 h 4 min 43 s) between the failure (15:04:21Z) and the base-apply 2 PASS (16:09:04Z), of which the upload itself was about 52 minutes.
- Spend: not recorded as separately measured; no cost figure for the retried upload exists in the evidence.
- Not affected: the next blocks (ACM validation, EMR upload and enable) ran afterward on the repaired state.

## Root cause

Direct cause: the S3 multipart upload part timed out ("Your socket connection to the server was not read from or written to within the timeout period") after the AWS CLI's retry limit (2), under the default upload concurrency, which this record does not know (not recorded).

Underlying cause: the coordinator attributes it to a slow uplink ("Upload took about 52 min with max_concurrent_requests 2 (slow uplink)", decision log line 23). The actual uplink rate, network conditions at 14:50-15:04Z, and whether any other traffic competed were not recorded, so the attribution is the coordinator's, not measured. The success with concurrency 2 is consistent with that attribution, but one success does not prove it.

## Trace and run IDs

- Base-apply 1: `20261118T145040Z-74189`; dry run `20261118T145000Z-73738`.
- Recovery plan: `20261118T151242Z-76267` (approved plan sha256 prefix 9078b23b, receipt prefix c3a5e36c).
- Base-apply 2: `20261118T151409Z-77117`; manifest `deploy-manifest-base-apply-20261118T151409Z-77117.json` (private, under the release directory).
- Original approved plan: run `20261118T144713Z-72996` (plan sha256 prefix 8e3a3704).

## Recovery and the human decision behind it

Human decision "A" at 15:08:39Z (quoted in the timeline). It kept the rule that a failed mutating run is not re-run: the recovery used a new no-change plan, a new record serial and a fresh dry run under the same reviewed script. The re-run is deviation 3 in `../agent-runs/phase-15/human-gate.md`, which the human accepted on 2026-11-20 ("Deviations 1-5 are accepted as disclosed").

## What was not done

- No re-run of base-apply 1 and no manual `aws s3 cp` outside the reviewed script.
- No Terraform change, no IAM widening and no resource change during recovery (the plan showed 0 changes).
- No measurement of the uplink; no re-measurement of upload time at other concurrency settings.

## Follow-ups

Proposals for the owners; none is decided.

| Item | Owner | Status |
|---|---|---|
| Add the `s3.max_concurrent_requests` setting and the wired-network advice for the 321 MB archive upload to the live runbook | documentation-engineer | Proposed |
| Consider a resumable or retry-extended upload mode in `deploy.sh` for large archives | infra-engineer | Proposed; not decided |
| Record a measured uplink figure before the next live upload | human / coordinator | Not recorded |

## Evidence

- `../agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md` (lines 18-23)
- `../agent-runs/phase-15/evidence/session-2/stage-a/stagea-results.txt`
- `../agent-runs/phase-15/evidence/session-2/stage-a/stagea-base-deltas.log`
- `../agent-runs/phase-15/evidence/session-2/stage-a/state-sha-after-stagea-base.log`
- `../agent-runs/phase-15/human-gate.md` (Stage a, deviation 3)
- `../agent-runs/phase-15/evidence/session-2/INDEX.md` (stage-a section)

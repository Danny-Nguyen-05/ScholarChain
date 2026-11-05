# Attempt 5: SUCCESS. G1 on EMR with Scala 2.13 matches the local baseline (2026-11-04)

Authority: human-approval.md Amendment 4 (window until 17:30 CST). All times are CST. The account ID and bucket name are redacted. The curated, redacted proof files are in [attempt5-proof/](attempt5-proof/). Raw outputs, including 112 EMR log files and the full collected results, are in `target/phase12d-spike-live/` (git-ignored, sha256 manifest).

1. **15:12:56 Preflight and plan** (deploy-engineer): `state list` empty; `Plan: 55 to add, 0 to change, 0 to destroy`; sha256 `82856112c97374f25ecec643127bf153b6fb69d9e04f2d75a426d10caae3ed8e`. The plan rule passed (the same 55 addresses and an equal shape). Code at commit `2d38f0f`, with the LZO codec override reviewed.
2. **Apply, run by the human:** "Apply complete! Resources: 55 added, 0 changed, 0 destroyed." The `shape` output equals the approval, and the rendered Spark defaults include the codec override.
3. **Cluster `j-…153M668H5I3`:** created 15:18:09, ready 15:22:27, ended 15:29:14. That is 11 min 5 s in total. NormalizedInstanceHours 16. Final state `TERMINATED`, `ALL_STEPS_COMPLETED`, so auto-termination after the steps worked.

| Step | State | Time |
|---|---|---|
| probe (Phase12Readiness, YARN cluster mode) | COMPLETED | 15:22:32–15:22:50 |
| g1 (Phase6Main, G1 fixture) | COMPLETED (`ret '0'`) | 15:22:55–15:26:39 |
| collect | COMPLETED | 15:26:44–15:26:52 |

## 12D verification (plan task 2)

| Requirement | Evidence | Result |
|---|---|---|
| The job completes | `steps-final-summary.json`, `cluster-final-summary.json` | ✅ All steps COMPLETED |
| Driver **and** executor class origins are Scala 2.13, not 2.12 | `probe-distributed.json`: driver (pid 7499) and a separate executor JVM (executor 2, pid 7623) both load `spark-core_2.13-3.5.4.jar`, `scala-library-2.13.14.jar` and `scala-reflect-2.13.14.jar`. `class-load-summary.json`: 6 YARN container JVMs (probe and G1 applications), 18 matches, all from `scala-library-2.13.14.jar` and `spark-core_2.13-3.5.4.jar`, and **0 files mentioning 2.12**. The coordinator re-derived these counts. | ✅ |
| DataFrame and Parquet read/write work | G1 reads its inputs and writes 28 Parquet tables through DataFrame `.parquet(...)`. The local comparison then read all 28 back. | ✅ |
| Output tables equal the local run's rows | `comparison.json`: `allExactRowsMatch=true`, `tablesCompared=28`, and every table `exactSchemaAndRowsMatch=true` (587 rows in total). Same `runId run:2047866e-0b89-4047-9a31-dccb2515c68d`, `codeVersion a4c1ad60…`, `hadoopManifestHash 4229afab…` and `entityResolutionManifestHash 1528d242…` as the baseline. `provenanceNormalization: none`. The coordinator re-checked it. | ✅ |

Notes:
- The comparison's own `cloudCompatibilityVerified=false` field is fixed by the readiness tool, not a result.
- Executors and the driver/AM ran on the single core node as separate YARN-container JVMs. This is the approved 1+1 shape.
- The security config in effect is Spark authentication plus AES-CTR network crypto (`authEngineVersion` 1) and IO encryption. Hadoop/YARN RPC is unencrypted inside the private subnet; this was disclosed and accepted.

## Evidence-collection defect (carried)

`collect-evidence.sh` exited 1 on macOS. The results tarball sha256 verified (`8a061770845eabb6b960443aec94c02ea039969a7821d1c32b2232e9df199082`), but macOS `tar` would not extract 28 `._SUCCESS.crc` entries (AppleDouble-style names), and `set -e` then stopped the script. The deploy-engineer extracted the tarball with Python `tarfile` instead and verified **241/241 files** against the on-node `files-manifest.sha256`, with 0 mismatches and 0 missing. That verified extraction was used for the comparison. The script needs a portable extractor; this is carried as item 31.

## Destroy

Run by the human. The first pass failed only on the known `aws_eip.nat` `DisassociateAddress` issue (item 24). The second pass reported "Destroy complete! Resources: 1 destroyed." **15:56 After-inventory** (deploy-engineer, read-only):
- `state list` is empty. `inventory.sh` exited 0 with `clean: true` and no billable resources remaining.
- Expected-retained: 5 KMS keys in PendingDeletion, one per attempt.
- Tagging-API residue: 29 security-group-rule ARNs and 4 vpc-endpoint ARNs. Direct describes return none of them.
- Bucket: 404. No clusters are active.
- Instances are terminated, the NAT gateway shows as deleted, and there are no EIPs, VPCs, volumes or EFS.

## Cost and elapsed time (all five attempts, modeled; Billing not yet reconciled)

| Attempt | Cluster | Instances | Ancillary lifetime (approx.) |
|---|---|---|---|
| 1 | none | none | ~15 min (EIP, EFS, KMS) |
| 2 | 1 min 43 s, validation failure | none | ~25 min |
| 3 | 4 min 39 s, bootstrap failure | 2 × ~3.5 min | ~20 min |
| 4 | 7 min 1 s | 2 × m5.xlarge, 16 normalized h | ~20 min |
| 5 | 11 min 5 s | 2 × m5.xlarge, 16 normalized h | ~25 min |

- **Compute:** EMR bills per second. Attempts 3–5 total about 22 min of two m5.xlarge, roughly 0.73 instance-hours: about 0.73 × (0.192 + 0.048) ≈ USD 0.18.
- **Ancillary:** NAT gateway plus public IPv4, about 1.75 h in total ≈ USD 0.09; NAT data, EFS, S3 requests and storage, a few cents.
- **KMS:** 5 keys pending deletion. Conservatively counted at USD 1 each for a month, that is USD 5, although they are scheduled to delete in 7 days.
- **Total:** roughly **USD 0.35 plus up to USD 5 KMS ≈ USD 5.35** before tax, under the USD 10 cap. The actual charges must be reconciled in the Billing console once the data arrives, usually within 24 h.
- **Wall time:** the first plan was at 11:19 CST and the final destroy at about 15:55 CST, including the four repair and review cycles.

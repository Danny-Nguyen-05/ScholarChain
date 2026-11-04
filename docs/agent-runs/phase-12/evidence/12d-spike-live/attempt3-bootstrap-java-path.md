# Attempt 3: instances launched, bootstrap failed on the Java path (2026-11-04)

Authority: human-approval.md Amendment 2 (13:56 CST). All times are CST. The account ID and bucket name are redacted. Raw outputs are in `target/phase12d-spike-live/` (git-ignored, sha256 manifest), including 29 EMR log files under `attempt3-emr-logs/` that were collected before the destroy.

1. **13:58 Preflight and plan** (deploy-engineer, `scholarchain-deployer-tf`): `state list` empty; `Plan: 55 to add, 0 to change, 0 to destroy`; sha256 `aeb4909312a50313fdafa8bc0dc84e3a6a4e3c717d177b0e3951b32e2d783f1b`. The plan rule passed (the same 55 addresses and an equal shape).
2. **Apply, run by the human:**
   - The network, EFS, S3 staging and IAM were created. Cluster `j-…6ABXSZFKOE` was created at 14:04:07.
   - **The boundary fix worked live.** Both m5.xlarge instances (primary `…f24a13`, core `…668d69`) launched at 14:04:16.
   - Terraform's waiter then reported "unexpected state 'TERMINATING'", with `BOOTSTRAP_FAILURE: On the master instance (…f24a13), bootstrap action 1 returned a non-zero return code`. As instructed, the human did not re-run the apply.
3. **Logs collected before the destroy** (deploy-engineer, read-only `s3 cp`): 29 files. The primary node's `bootstrap-actions/1/stderr` is complete at 6 lines (bucket redacted):

   ```
   [bootstrap] arming node shutdown in 114 minute(s) (max=120, uptime=1m, allowance=5m)
   Shutdown scheduled for Wed 2026-11-04 21:59:18 UTC, use 'shutdown -c' to cancel.
   [bootstrap] download s3://<bucket>/staging/runtime/scholarchain-runtime.tgz
   [bootstrap] sha256 ok: runtime tarball
   [bootstrap] sha256 ok: job jar
   [bootstrap] FATAL: no java at /usr/lib/jvm/java-17-amazon-corretto/bin/java
   ```

   - The controller logged exit code 4 (`bootstrap.sh`'s "Java" code) after 10 s on the primary node and 8 s on the core node.
   - The controller environment shows `JAVA_HOME=/etc/alternatives/jre` and `/usr/lib/jvm/jre-17/bin/java`.
4. **Instances:** both TERMINATED at 14:07:43, about 3.5 min after launch.
5. **Destroy, run by the human:** the first pass failed only on `aws_eip.nat`, a `DisassociateAddress` 403 on `…:*/*` (carried item 24). The second pass reported "Destroy complete! Resources: 1 destroyed."
6. **The single cluster attempt under Amendment 2 is spent.**
7. **14:11 After-inventory** (deploy-engineer, read-only):
   - `state list` empty; `inventory.sh` exit 0, `clean: true`, no billable resources remaining.
   - Expected-retained: 3 KMS keys in PendingDeletion.
   - Tagging-API residue: 26 security-group-rule ARNs and 2 vpc-endpoint ARNs. The direct describes find none of them, so this is tagging-API lag.
   - Bucket: 404. No active clusters.
   - The cluster's final state is `TERMINATED_WITH_ERRORS`, ended at 14:08:46, 4 min 39 s after creation. Both instances are terminated; no EIPs, VPCs, volumes or EFS remain, and the NAT gateway shows as deleted.

**Proven live by this attempt:**
- deployer IAM and boundary for network, EFS, S3, KMS and the EMR service role;
- EMR RunInstances with encrypted gp3 volumes;
- a private subnet with no public IPs;
- the 321 MB staging upload with `credential_process` refresh;
- bootstrap download and sha256 verification of the runtime and job JAR;
- the hard shutdown timer arming first (114 min).

**Not yet proven:** the EFS mount, the Spark 3.5.4/Scala 2.13 runtime on YARN, the driver and executor class origins, and the G1 job output. No Spark step ran.

**Root cause:** the hard-coded Java path came from a re:Post article and does not exist on the EMR 7.8.0 AMI. The fix is to resolve Java 17 at runtime: prefer `/usr/lib/jvm/jre-17`, verify `java -version` reports 17, and fail otherwise. The same path is used for `spark.yarn.appMasterEnv.JAVA_HOME` and `spark.executorEnv.JAVA_HOME` in the Spark defaults.

**Cost exposure:** two m5.xlarge instances with EMR for about 3.5 min (about USD 0.03), the NAT gateway and EIP for about 20 min, EFS, S3 and the KMS key allowance. Under about USD 0.20 plus KMS.

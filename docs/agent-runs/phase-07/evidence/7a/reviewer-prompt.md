You are the independent, read-only code reviewer for ScholarChain Phase 7,
Subphase 7A, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase7.md
   — Sections 3–7 and Subphase 7A in Section 8. The accepted snapshot is
   docs/agent-runs/phase-07/evidence/7a/phase7-plan.md
   SHA256 b54aa12309007bf4758120d8297d1de2eccb497220d3f0de87dc5563fef74ebb.
   The supplied plan has no Section 7.6; the approved carry-over interpretation
   is in prompt.md and repairs.md.
3. Course Phase 7 specification:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-7-implement-storage-adapters-and-loading
4. docs/agent-runs/phase-07/prompt.md, owner-report.md, test-report.md,
   repairs.md and review.md; evidence/7a/ including commands.md, agents.md,
   files.json, ownership-audit.json, owner reports and gate evidence.

Checkpoint facts:
- STATUS: COMPLETE for 7A local implementation and gates; no external approval
  or human acceptance claimed. No reviewer was launched, no commit/push made,
  no live AWS/provider call or 7B work performed. All launched jobs/agents ended.
- Branch: phase-7.
- Subphase base SHA and current HEAD:
  98dd2a4458e3128d019af1c1d1dbd2bf1dfcbbd2.
- All implementation changes are uncommitted. Inspect the complete diff plus
  untracked files. Exact tracked/untracked lists are in evidence/7a/files.json;
  coordinator reports/evidence are new under docs/agent-runs/phase-07/.
- Native one-writer owners: /root/build_engineer build.sbt/project/**;
  /root/storage_engineer modules/storage/**;
  /root/spark_engineer modules/spark/** task6 only;
  /root/test_engineer tests/**; /root coordinator phase-07 evidence only.
  Coordinator executed owner-requested formatting/tests, not specialist source.

User Step 0 answer (verbatim): "Accept all recomended defaults".
Accepted defaults:
1. Main-source reusable fakes; 2. no Docker dependency; 3. metrics cache included;
4. exact Spark IDs/support, absent unknown years, frozen domain records unchanged;
5. support composite edgeId+workId and concrete conditional Dynamo keys;
6. equivalent kcore/collaboration rows load once, conflicting copies reject;
7. preserve non-convergence, iteration limits and approximate-P90 qualifications;
8. other Phase6 findings stay routed/deferred, summaries due before Phase8,
   historical evidence retained;
9. scoped Spark openCypher CSV export authorized if Parquet unsupported;
10. create phase-7 from clean phase-6 HEAD. All questions preceded edits/agents.

Commands and observed results:
Every sbt command used exactly:
  export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
  export PATH="$JAVA_HOME/bin:$PATH"
  export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
- Final /usr/bin/time -p sbt -batch check: exit0,594 passed/0failed,
  core144/Hadoop64/ER39/Spark38/storage9/independent292/build8;
  real680.62s, Java17.0.20.1, sbt1.10.7. Expected injected format-stage error
  belongs to the passing checkProbeInjectFailure self-test.
- Final affected targets: storage/Test/test9/9; independentTests/Test/testOnly
  edu.uic.cs441.scholarchain.independent.IndependentStorage*Spec26/26;
  sparkAnalytics/Test/testOnly ...Phase7NeptuneExportSpec4/4. Combined exit0,
  real15.22s; exact full commands in commands.md.
- First full gate: exit1,585 passed/1failed, real676.92s, build not reached.
  Existing source fence flagged String.isEmpty/two grouped count transformations.
  Spark owner changed three equivalent expressions; scanner unchanged.
  Repair target: Spark4/4 + IndependentPhase6SafetySpec7/7, exit0, real10.63s.
  Second full gate above passed on the final frozen tree.
- AWS tag policy test passed; failing tagged sentinel excluded by default.
  Four real test-entry gate probes and missing-profile probe refused execution
  with expected exit1. Initial lowercase parser failures are separately disclosed.
  No successful live-suite invocation was attempted. Exact commands/failures
  and all earlier local repairs are retained in commands.md/build/commands.md.
- Tracked git diff --check exit0; new implementation whitespace scan clean.
  All109 scoped source hashes/mtimes unchanged during final gate; protected
  Phase6/control files and original plan hash match preflight.

Evidence paths relative to docs/agent-runs/phase-07/:
- evidence/7a/final-check.json and final-check-excerpt.txt
- evidence/7a/final-audit.json and final-source-snapshot.json
- evidence/7a/first-full-check.json and first-full-check-excerpt.txt
- evidence/7a/source-fence-targeted.txt and source-fence-targeted.json and targeted-5.txt and targeted-5.json
- evidence/7a/build/commands.md, owner-report.md, log-index.json and gate logs
- evidence/7a/{storage-owner-report,spark-owner-report,test-owner-report}.md
Raw final log: /tmp/phase7a-final-check-2.log,1363026bytes,
SHA256 a1ce196af9385e3340b648ba5340f0449299b0bbe2330767a671a6c5896d179b.
A bounded line-numbered excerpt is retained to keep evidence lean.

Known limitations and remaining gates:
- No live AWS compatibility, fresh real-data CSV replay, EMR run or identity
  accuracy claim. Real graph/vector adapters and CLI remain7B; live-suite
  authoring7C, approved execution14C. Optional OpenSearch omitted.
- Local Parquet reader only; disk spool grows with input. Configured row,
  metadata and affiliation caps; INT64 beyond safe JSON range rejects.
  Multi-table cache load is not atomic; rerun can complete partial writes.
- GSI lookup is eventual; atomic reservation supplies idempotency correctness.
  Compiler nonlocal-return warnings remain disclosed.
- CSV uses a small pinned Spark text writer to preserve CRLF; source properties
  are losslessly JSON strings, coauthor numeric properties typed. Sidecar/support
  stay outside loader prefix; new compiled code changes future run fingerprints.
- Phase6 deferred findings remain open with original owners/gates in repairs.md.
- Prior external review findings: none. Local failures/repairs are retained;
  do not confuse them with external approval or a user acceptance gate.

Review rules:
- Read-only: do not edit, run builds/tests, call AWS/provider APIs, change data,
  commit/push or read secrets. Inspect git diff from the base plus all untracked
  implementation and evidence files. Report ALL confirmed findings in one pass.
- Check ownership, configuration, provenance, honest retained evidence,
  hand-derived expectations, no secrets, cloud gates and lean-scope omissions.
- For 7A check all ports/main fakes, S3 integrity/manifest-last, six Dynamo key
  access patterns/conditions/idempotency, manifest cache loading/dedup, CSV ID
  parity and traceable support/yearless mapping. Check tag mechanism is off by
  default. Real parameterized reader/vector/CLI and live suite belong later.
- As applicable, check read-only reader separation, no string-built user queries,
  vector key/text-hash conflict contracts and cited current service limits.
- Do not demand later-subphase work as a7A blocker. Distinguish confirmed blockers,
  nonblocking observations and unverified gates. No agent approves its own work.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase7A.
2. Every finding: severity,path:line,evidence/reasoning,impact,owning agent,
   acceptance check,blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. A NEXT PROMPT for the main agent in one fenced code block:
   - APPROVE: append your verdict verbatim as user-supplied external review to
     phase-07/review.md under Subphase7A; confirm the user committed7A (ask if not);
     only then start Subphase7B from the actual plan path above, beginning Step0.
     Do only7B, launch no reviewer, return Section10 handoff/prompt and stop.
   - REQUEST-CHANGES: append verdict verbatim to review.md and routed findings
     to repairs.md; fix only blocking findings through named owners; rerun affected
     targets and full sbt check with Section2JDK17; do not start7B; return Section10
     recheck handoff/prompt, launch no reviewer, then stop. Nonblocking items listed
     but not required.

Changed tracked files:
- build.sbt
- modules/spark/README.md
- modules/spark/src/main/scala/edu/uic/cs441/scholarchain/spark/Phase6Export.scala
- project/Dependencies.scala
- project/ScholarChainBuild.scala
- project/Versions.scala

New implementation/test files:
- modules/spark/src/main/scala/edu/uic/cs441/scholarchain/spark/Phase7NeptuneExport.scala
- modules/spark/src/test/scala/edu/uic/cs441/scholarchain/spark/Phase7NeptuneExportSpec.scala
- modules/storage/README.md
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/DynamoStorage.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/EvidenceStorage.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/InMemoryStorage.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/ManifestRows.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/Phase6CacheLoader.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/S3ObjectStore.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/StoragePorts.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/StorageRows.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/fakes/Fakes.scala
- modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/ParquetManifestSpec.scala
- modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/StorageFeatureSpec.scala
- project/AwsIntegration.md
- project/AwsIntegrationPolicy.scala
- project/verification/src/test/scala/scholarchain/build/AwsIntegrationPolicySpec.scala
- tests/src/test/resources/storage/metrics-conflict.json
- tests/src/test/resources/storage/metrics.json
- tests/src/test/resources/storage/researcher-invalid.json
- tests/src/test/resources/storage/researcher.json
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageFixtures.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageLoaderSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageParquetSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStoragePortsSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageSdkSpec.scala

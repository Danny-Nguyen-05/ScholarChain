STATUS: COMPLETE for build-owner wiring and targeted checks; stable-tree gate pending.
OWNER: /root/build_engineer (native Codex role; model inherited).
WORK ORDER: Phase 7A task 1, plus necessary Parquet loader dependencies and storage access for independentTests.
FILES CREATED: project/AwsIntegrationPolicy.scala; project/AwsIntegration.md; project/verification/src/test/scala/scholarchain/build/AwsIntegrationPolicySpec.scala.
FILES MODIFIED: build.sbt; project/Dependencies.scala; project/ScholarChainBuild.scala; project/Versions.scala.
COMMANDS RUN: Exact command sequence in commands.md, always Section 2 JDK17 environment. java -version exit0, first sandbox sbt exit1 (cache lock), escalated target exit0, four lowercase parser probes exit1 (not guard proof), four corrected guard probes exit1 (expected), missing-profile probe exit1 (expected), resolution/format exit0, WIP dependencyClasspath exit1, externalDependencyClasspath exit0. Retained logs/index in this directory.
TEST RESULTS: AwsIntegrationPolicySpec 1 passed; deliberately failing tagged sentinel excluded; four correct gate entry points and missing-profile refusal observed. No live suite execution.
VALIDATION RESULTS: SDK s3/dynamodb/neptunedata/s3vectors 2.56.0 resolve; parquet-hadoop1.13.1 and Hadoop3.3.6 runtime support native Parquet without Spark storage dependency. Independent classpath295 entries, one SLF4J provider log4j-slf4j2-impl2.20.0, no logback-classic/reload4j. Default tests -l tag; AwsIntegration -n tag plus required opt-in+nonblank profile. See exact logs.
ASSUMPTIONS: Explicit AWS_PROFILE including deliberately selected default is profile selection, not permission for cloud writes.
RISKS: WIP storage compilation errors routed to storage owner; not a final-tree result. Full sbt check pending. Successful live path remains unrun.
MANUAL ACTION REQUIRED: Independent user-launched review after final gate; no reviewer triggered.
BLOCKED-ON OWNER: None for build wiring.
BLOCKED-ON EVIDENCE: Stable-tree whole repository check pending.
NEXT GATE: Affected targets, full JDK17 check, then user review.

Sources: https://github.com/aws/aws-sdk-java-v2/releases/tag/2.56.0 (2026-10-14, checked2026-10-22); https://github.com/apache/spark/blob/v3.5.4/pom.xml.


Repair round 1 F2 retention correction: all retained build logs are now Git-visible .txt files listed in log-index.json. Original /tmp .log paths remain execution-history references. Recorded raw SHA256 hashes were reverified; retained hashes/bytes are now explicit, including the provider classpath excerpt which differs from its full raw log. .gitignore was not edited. No guard result or raw content changed.

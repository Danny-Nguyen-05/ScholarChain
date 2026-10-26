STATUS: COMPLETE implementation; compilation/full gate unverified at owner handoff.
OWNER: /root/build_engineer
WORK ORDER: Phase 8A pinned SDK entries and independent-test dependency wiring.
FILES CREATED: None.
FILES MODIFIED: build.sbt; project/Dependencies.scala.
COMMANDS RUN: Read assigned instructions/plan/build files; applied scoped patch; git diff --check -- build.sbt project/Dependencies.scala and git diff --stat -- build.sbt project/Dependencies.scala, exit 0.
TEST RESULTS: No sbt command run; coordinator holds shared slot.
VALIDATION RESULTS: SQS supplied to storage, Bedrock Runtime to rag, reuse AWS SDK2.56.0. Independent tests depend on rag. Existing live-test exclusion/check implementation unchanged.
ASSUMPTIONS: Existing SDK version authoritative; shared core embedding port prevents a cycle.
RISKS: Dependency resolution/compilation pending coordinator gates.
MANUAL ACTION REQUIRED: Coordinator runs formatting/affected/full gates on JDK17.
BLOCKED-ON OWNER: None for build authorship.
BLOCKED-ON EVIDENCE: Compilation/tests pending at owner handoff.
NEXT GATE: Affected/full gates, then user-launched independent review.

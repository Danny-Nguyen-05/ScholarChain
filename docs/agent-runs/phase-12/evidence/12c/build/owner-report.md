STATUS: COMPLETE (observed full gate; coordinator completes XML collection)
OWNER: build-engineer /root/build_12c; coordinator report assembly
WORK ORDER: Full JDK 17 check after the final 12C source freeze, base 3b0855b9657a72b30e8ac43bd484161a9b886c79.
FILES CREATED: Scratch runner/log/snapshots/results in /tmp/scholarchain-phase12c-build; curated copies here.
FILES MODIFIED: No authored source or human-owned files. Build outputs only.
COMMANDS RUN: Exact JDK17 JAVA_HOME/PATH/SBT_OPTS environment, java -version, sbt -batch check; commands.json records start/end/cwd/exits.
TEST RESULTS: Full gate exit 0, 1,255 tests, 157/157 fresh XML, zero failures/errors/skips. The expected checkProbeInjectFailure self-test is the only error block. Runner's original149 XML / 1,242 count omitted build-verification; coordinator re-parsed thoseeight fresh XML reports / 13 tests and retained the original report unchanged.
VALIDATION RESULTS: 3,565 before/after snapshot inputs equal and current hashes/bytes/mtime match;190 frozen infrastructure/test files unchanged. Gate started2026-10-30T17:42:32.864369+00:00 after freeze 17:40:28.200020Z; ended2026-10-30T17:54:33.788049+00:00. sbt wall720.852s, reported718s; totalwrapperwall724.918s. raw SHA-256 19d0959878981057976b356a23a02589fc9e20e3821ae52f35b2b500b2a8f5dc;gzip SHA-256 70c405d6d92ac733511945b95bc6ea16831598cf95ec8e5ccdfa66facd004095;decompression verified.
ASSUMPTIONS: Legacy project/verification target XML is outside the active gate and excluded; all active modules/tests/build-verification XML were fresh.
RISKS: Offline repository gate does not exercise live deployment/KMS/runtime or measure cost.
MANUAL ACTION REQUIRED: Coordinator integrates final reports and requests user-launched read-only review.
BLOCKED-ON OWNER: None for build gate.
BLOCKED-ON EVIDENCE: None for observed gate.
NEXT GATE: Independent read-only 12C review; no jobs remain.

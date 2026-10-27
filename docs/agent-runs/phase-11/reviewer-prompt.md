You are the independent, read-only code reviewer for ScholarChain Phase 11,
Subphase 11A, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase11.md
   — Sections 3–7 and Subphase 11A in Section 8: scope, owners, questions,
   tasks and Done when.
3. The course Phase 11 specification, Required test inventory and deductions:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-11-adversarial-testing-and-full-repository-review
4. docs/agent-runs/phase-11/prompt.md, owner-report.md, test-report.md,
   repairs.md, review.md and evidence/11a/.

Checkpoint facts:
- Branch: phase-11
- Subphase base SHA and current HEAD: 0c5ee89994b5b738a3490ef5e8f032fdc67327b2
- Changed tracked files: none. No commits or pushes.
- Untracked test files, under tests/src/test/scala/edu/uic/cs441/scholarchain/independent/:
  AdversarialBlockingReplaySpec.scala, AdversarialDataPlaneSpec.scala, AdversarialGraphShapesSpec.scala.
- Untracked files under docs/agent-runs/phase-11/:
  owner-report.md, prompt.md, repairs.md, review.md, reviewer-prompt.md, test-report.md.
- Untracked files under docs/agent-runs/phase-11/evidence/11a/:
  baseline-test-counts.json, collect-evidence.py, commands.json, coverage-validation.json, coverage.json, defects.json, development-runs.json, final-validation.json, full-check-excerpt.txt, full-check-exit.txt, full-check-start.json, full-check-summary.json, git-status.txt, handoff-files.json, inventory-before.md, java-version.txt, new-tests.json, phase11a-targeted-1-excerpt.txt, phase11a-targeted-2-excerpt.txt, phase11a-targeted-3-excerpt.txt, preflight.json, protected-source-before.json, reading-ledger.json, test-engineer-handoff.md.
- Exact path inventory: evidence/11a/handoff-files.json and git-status.txt.
- Step 0 answers: ExposedDefect tags and explicit defect runs, build-engineer
  exclusion if needed; requirement-to-test table and exact counts without
  coverage tooling; later 11C uses 0349388 plus whole-repository review.
- Native test-engineer task: /root/test_engineer_11a; sole tests writer,
  inherited model revision unavailable. Coordinator assembled evidence and
  ran final gates. No reviewer or nested delegation was launched.

Observed commands/results (cwd is repository root):
All sbt commands used:
  export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
  export PATH="$JAVA_HOME/bin:$PATH"
  export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
- java -version: exit 0, OpenJDK 17.0.20.1.
- sbt -batch 'independentTests / Test / scalafmt' 'independentTests / Test / testOnly *Adversarial*':
  first sandbox attempt exit 1 before startup; child escalation aborted without
  execution; coordinator attempt 2 exit 1 on new-test Scala indentation;
  corrected attempt 3 exit 0,19/19 tests in 4 suites (15 new + 4 existing).
  Final sparse-author cardinality assertion arrived after targeted compilation;
  final full check verified its frozen source.
- /usr/bin/time -p sbt -batch check > /tmp/phase11a-final-check.log 2>&1:
  exit 0, 1231 passed / 0 failed / 0 errors / 0 skipped in 152 fresh JUnit reports;
  core 207 / Hadoop 64 / ER 39 / Spark 38 / storage 80 / RAG 107 / services 36 / independent 647 / build 13.
  sbt 728 s, real 730.49 s; expected nested injected-failure self-test passed,
  then success marker written.
- python3 docs/agent-runs/phase-11/evidence/11a/collect-evidence.py:
  exit 0; log totals match fresh XML, all 45 mapped tests present,
  three new-source hashes and 346 protected tracked source/config hashes match.
- git diff --check: exit 0. Exact wrappers/redirects in commands.json.
- Full raw log SHA256: 07f515f3f51427dac4a730bf2ab0af39c3c7d005111b335b7c6c6a78fff32758,
  1717764 bytes. Raw logs in /tmp; durable excerpts and hashes under evidence/11a/.
- Coverage: all 11 data categories, 45 distinct selected tests (30 existing + 15 new),
  eight mutation thought checks; category mappings overlap by design.
- ExposedDefect 0: no production defect exposed by these runs; no tag/build
  exclusion or empty defect run needed. Earlier findings retain original status.

Limits/future scope:
- Local synthetic fixtures; no live AWS/paid provider/EMR/scale/accuracy claim.
- Bridge measures use a declared partition; prior LPA/P90 and Phase 5 evaluation
  limits remain. Replay hashes establish equality for tested local inputs.
- Runtime categories 12–20 are 11B; full-repository review/production repair is 11C.
  Existing committed runtime resolver cases are reused for common-name coverage;
  no runtime adversarial implementation was started.
- Readings covered relevant contracts, README sections and all prior reports'
  active final/risk/disposition sections, not every historical line; disclosed
  in reading-ledger.json. Raw /tmp logs are not durable across reboot.
- No prior 11A review/repair round; new-test compile correction retained honestly.

Review rules:
- Read-only: no edits, builds/tests, AWS/provider calls, data changes, commits,
  pushes or secret reads. No delegation to an implementation agent.
- Inspect git diff 0c5ee89994b5b738a3490ef5e8f032fdc67327b2 plus ALL untracked files.
  Report all confirmed findings in one pass.
- Check one-writer ownership, test-only specialist changes, public-interface
  tests, hand-derived expectations, independent oracles and meaningful bounds.
  Confirm complete category mapping and exact counts against source/evidence.
- Check no hardcoded production endpoints/buckets/accounts/models, secrets in
  files/logs/evidence, invented provenance or unobserved claimed passes.
  Declared synthetic fixture values and test-bound limits are test inputs.
- Check ExposedDefect cases are listed if any; no silently hidden failures.
  Confirm production/build paths unchanged, original limitations carried,
  cloud/spend gates respected and optional work omitted as recorded.
- Assess disclosed reading and raw-log retention limits against the work order.
- Do not demand 11B/11C/later deployment work as 11A implementation. Distinguish
  blocking findings, nonblocking observations and unverified future gates.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase 11A.
2. Every finding: severity, path:line, concrete failure input/evidence, impact,
   owning agent, acceptance check and blocking yes/no. Verify against files.
3. The report fields required by docs/agent-runs/README.md.
4. A complete NEXT PROMPT in one fenced code block for the user to paste:
   - On APPROVE: include the complete verdict verbatim; tell the main agent to
     append it to phase-11/review.md under Subphase 11A as user-supplied external
     review, confirm the user committed 11A (ask if not), then start ONLY 11B of
     the same external phase11.md with Step 0 questions. Require its review
     handoff/prompt and stop before 11C. Never trigger a reviewer.
   - On REQUEST-CHANGES: include the complete verdict/findings; tell the main
     agent to append them to review.md/repairs.md, route each blocking finding
     to its owner, rerun affected tests and full JDK 17 sbt check, return the
     Section 10 recheck prompt, and stop without starting 11B. Nonblocking items
     remain logged unless separately authorized. No agent commits/pushes or
     writes human decisions.

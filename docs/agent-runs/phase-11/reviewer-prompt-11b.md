# Subphase 11B reviewer prompt

```text
You are the independent, read-only code reviewer for ScholarChain Phase 11,
Subphase 11B (initial handoff), in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase11.md
   Sections 3–7, Section 8 Subphase 11B, and Section 10.
3. The course Phase 11 specification:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-11-adversarial-testing-and-full-repository-review
4. docs/agent-runs/phase-11/prompt.md, owner-report.md, test-report.md,
   repairs.md and review.md, focusing on appended 11B sections and the
   retained user-supplied 11A APPROVE/N1–N5. Read evidence/11b/ below.

Checkpoint facts:
- Status: COMPLETE for implementation/local gates; independent review pending.
- Branch: phase-11. Base SHA and current HEAD:
  d80afb755c649ecc5cda60525a1a0201aceb4c03 (committed/pushed 11A).
  Phase 9/10 ancestry verified, including Phase 10 HEAD
  0c5ee89994b5b738a3490ef5e8f032fdc67327b2. No 11B commit/push.
- Changed tracked files: only appended 11B content in these files under
  docs/agent-runs/phase-11/: owner-report.md, prompt.md, repairs.md,
  review.md, test-report.md.
- New test files, sole writer /root/test_engineer_11b, under
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/:
  AdversarialRuntimeBoundarySpec.scala, AdversarialRuntimeFixture.scala,
  AdversarialRuntimeHttpSpec.scala, AdversarialRuntimeWorkflowSpec.scala.
  Other new files: docs/agent-runs/phase-11/reviewer-prompt-11b.md and
  the evidence/11b/ files enumerated below and in handoff-files.json.
- No Step 0 questions remained; coordinator explicitly stated that before
  edits. Prior user answers persist: ExposedDefect tags with explicit runs
  and build-engineer exclusion only if needed; exact requirement-to-test
  table/counts without a coverage tool. The recorded later 11C baseline is
  0349388 plus whole repository; no 11C work was performed here.
- Test-engineer stopped writing before every gate. Coordinator formatting
  explicitly rewrote four new files, then only Http after the owner's fix.
  No specialist sbt calls. No nested agents, reviewer invocation, production
  edits, cloud/provider calls or human-decision records. Agent completed;
  all builds finished. Exact inherited model revision unavailable.

Commands and observed results:
Every sbt command used this exact environment, at the repository root:
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
- java -version: exit 0, OpenJDK 17.0.20.1; sbt 1.10.7.
- sbt -batch 'independentTests / Test / scalafmt': format-1 exit 0,
  rewrote all four new sources.
- sbt -batch 'independentTests / Test / scalafmtCheck'
  'independentTests / Test / testOnly *AdversarialRuntime*': targeted-1
  exit 1, unavailable Logback classes in new test; zero tests ran.
  Test-engineer corrected capture to existing Log4j2; no dependency change.
- Same formatter command: format-2 exit 0, rewrote only new HTTP suite.
- Same targeted command: targeted-2 exit 0, format check passed,
  17/17 in 3 suites, zero failed/canceled/ignored/pending.
- /usr/bin/time -p sbt -batch check: exit 0; 1,248/1,248 in 155 fresh reports;
  zero failures/errors/skips; sbt 720 s, wall 722.37 s. Independent 664/89 reports;
  other modules 571; build-verification 13. Historical baseline 1,231/152 reports.
  Expected nested injected format-stage failure self-test; outer check passed.
- python3 docs/agent-runs/phase-11/evidence/11b/collect-evidence.py: exit 0;
  fresh JUnit/log totals, all 38 mapped cases and final frozen sources verified.
  448 protected tracked files unchanged: 304 module, 24 build, 115 existing
  independent-test, 5 prompt-asset files (resources included).
- Start records created once immediately before launch and never rewritten.
  Final validation checks the full-start hash/mtime and source fingerprints.
- Combined 11A + 11B ExposedDefect count 0; no tagged/ignored/quarantined new
  cases, exclusion wiring or explicit defect run needed for the empty list.
  Earlier registered findings remain open under their original dispositions.

Coverage and test oracles:
- 17 new tests: Boundary 3, Workflow 8, HTTP 6; 21 existing + 17 new = 38 distinct.
- Categories 12–20 existing/new counts respectively:
  12=3/2,13=4/6,14=2/3,15=2/9,16=2/3,17=2/3,18=4/3,19=1/1,20=1/1.
  Category counts overlap; exact names in test-report.md and coverage.json.
- Inspect real ingestion→retrieval→synthesis→verification→audit and actual
  local HTTP injection of title instruction, abstract tool-call/delimiter,
  fullText fake-plan JSON. Healthy same-composition count 3 must be accepted;
  malicious 999, invented subject and nonexistent evidence must be rejected.
- Check fault injection really enters blocked GraphReader, rejected VectorStore
  and conditional session-CAS paths; invocation/cancellation/recovery checks
  must distinguish success from an unexercised fault. Existing worker case
  supplies duplicate-message replay; new HTTP cases exercise key/body replay.
- Nine runtime mutation thought checks are reasoned, not executed mutations.
- Config/header/exception redaction observes HTTP request events, runtime-stage
  logger events and HTTP responses/headers, with positive capture assertions.

Evidence: docs/agent-runs/phase-11/evidence/11b/
  baseline-test-counts.json, collect-evidence.py, commands.json, coverage-validation.json, coverage.json, defects.json, final-validation.json, format-1-excerpt.txt, format-1-result.json, format-1-start.json, format-2-excerpt.txt, format-2-result.json, format-2-start.json, full-check-excerpt.txt, full-check-result.json, full-check-start.json, full-check-summary.json, full-start-file-stamp.json, git-status.txt, handoff-files.json, inventory-before.json, java-version.txt, mutation-spot-checks.json, new-tests.json, preflight.json, protected-source-before.json, reading-ledger.json, run-gate.py, targeted-1-excerpt.txt, targeted-1-result.json, targeted-1-start.json, targeted-2-excerpt.txt, targeted-2-result.json, targeted-2-start.json, test-engineer-handoff.md, writing-barrier.json.
Raw full log: /tmp/phase11b-full-check.log; 1,721,327 bytes;
SHA-256 142d10e1518e579d76a45f6a4c2db93771d496105f777a8f301ebf03559cfb31.
Other raw logs: /tmp/phase11b-format-1.log, targeted-1.log, format-2.log,
targeted-2.log (each uses the same phase11b- prefix). Hashes in commands.json.

Limitations/deferred work:
Synthetic local fakes/scripted model; bounded plan supplied by HTTP adapter;
existing planner tests cover planning. Fault fakes test ports, selected adapter
tests cover SDK retry behavior. No general live-model injection resistance,
AWS compatibility, deployed authorization, scale, throughput or cost claim.
Redaction capture is scoped to the two stated event surfaces. Required missing
service credentials yield the documented generic configuration error. Historical
report reading is a disclosed active-disposition scan, not a line-by-line reread.
Raw logs are only in /tmp and not reboot-durable; excerpts/hashes retained.
Carry prior Phase 5–10 limits and 11A N1–N5. N1/N2 process lessons applied;
N3/N4 were not repaired or investigated. No optional coverage tool/OpenSearch/
index/service/CI work. 11C whole-repository review/repairs and Phase 14 live gates
remain future scope. Independent review/human gate/commit remain user actions.
No repair round in 11B; no prior finding is silently closed by passing tests.

Review rules:
- Read-only. Do not edit files, run builds/tests, call AWS/providers, change
  data, commit/push or read secrets.
- Inspect git diff d80afb755c649ecc5cda60525a1a0201aceb4c03 plus all
  untracked files in handoff-files.json; report all confirmed findings once.
- Check one writer per path per docs/agents.md and plan Section 5; no production
  edits; no hardcoded live buckets/endpoints/accounts/models; no secrets;
  honest retained evidence; requirement-derived, meaningful assertions;
  real injected faults; exact coverage/count reconciliation; defect retention;
  cloud/spend gates; lean-scope omissions. Re-derive expectations from fixtures.
- Verify immutable start records, stopped-writing barriers and explicit formatter
  rewrites (11A N1/N2 lessons). Do not launch another reviewer.
- Do not demand later-subphase work; distinguish blockers, nonblocking
  observations and unverified future gates. Full repository review is 11C.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase 11B.
2. Every finding: severity, path:line, evidence, concrete input/impact,
   owning agent, acceptance check and blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. A complete NEXT PROMPT in one fenced code block for the coordinator:
   If APPROVE: append your verdict verbatim under Subphase 11B in review.md,
   marked user-supplied external review; confirm the user committed 11B
   (ask and wait if not); then start ONLY 11C of the external phase11.md,
   beginning with Step 0 and respecting the recorded baseline choice. Return
   its complete Section 10 reviewer prompt without invoking any reviewer and
   stop at that one-subphase boundary. No human gate/approval record writing.
   If REQUEST-CHANGES: append verdict verbatim and findings to repairs.md;
   route blocking findings only to their owners; preserve production freeze
   for test work, retain/report exposed defects; rerun affected tests and full
   JDK 17 check; return the complete Section 10 recheck prompt and stop. Log
   nonblocking findings without treating them as required repairs. No 11C.
```

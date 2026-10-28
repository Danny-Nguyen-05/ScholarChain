You are the independent, READ-ONLY reviewer for ScholarChain Phase 11,
Subphase 11C repair round 1, batch 1, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase11.md
   §§2–7.4, §8 Subphase 11C, §§9–11.
3. The primary course Phase 11 specification, Required test inventory and deductions:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-11-adversarial-testing-and-full-repository-review
4. docs/agent-runs/phase-11/prompt.md, owner-report.md, test-report.md,
   review.md, repairs.md, especially initial 11C REQUEST_CHANGES and repair-round 1 sections.
5. docs/agent-runs/phase-11/evidence/11c-r1/README.md, preflight.json,
   step-0.json, delegation.json, both specialist owner reports, red-reproduction.json,
   commands.json, all gate start/result/excerpts, coverage.md/coverage.json,
   full-check-summary.json, defects.json, final-validation.json, handoff-files.json.
   Inspect actual source/tests and retained raw logs where available.
6. Initial whole-repository packet evidence/11c/, reviewer-prompt-11c.md and all
   module READMEs/earlier phase registers as needed. Historical pending checkpoints
   do not override later external dispositions; do not rerun old collectors.

Checkpoint facts:
- Branch phase-11. Repair-round base/current HEAD:
  2b0aee044f243f01bbb603170d09f5c507df8bb7. Initial 11C assembly was uncommitted and is preserved.
- User-confirmed whole-repository baseline 03493882399e9020e6892c9f97e0ec8919365215.
  Review all repository files at HEAD plus the baseline-to-HEAD diff,
  `git diff 2b0aee044f243f01bbb603170d09f5c507df8bb7` and ALL untracked files. No repair commit exists.
- Changed tracked paths: modules/services/README.md;
  modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/QueryService.scala;
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/AdversarialRuntimeHttpSpec.scala;
  docs/agent-runs/phase-11/{prompt,owner-report,test-report,review,repairs}.md.
- Untracked: new service module SessionBindingRecoverySpec.scala at
  modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/;
  docs/agent-runs/phase-11/reviewer-prompt-11c.md and reviewer-prompt-11c-r1.md;
  initial evidence/11c/ (12 files), current evidence/11c-r1/ (50 files).
  Total status: 8 modified tracked files and 65 untracked files; exact paths are
  in evidence/11c-r1/handoff-files.json. Verify every actual file against it.
- Step 0 user selected “Yes, include R11C-5 (Recommended)”. Scope ONLY blocking
  R11C-1/R11C-2 plus same-owner README R11C-5. ExposedDefect tags/explicit runs
  if needed, exact requirement tables and no coverage tool remain prior decisions.
- Coordinator ran all sbt commands with plan§2 JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home,
  PATH=$JAVA_HOME/bin:$PATH, SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml.
  java -version exit0: OpenJDK 17.0.20.1; sbt 1.10.7.
- Actual red gate: `sbt -batch 'services / Test / scalafmtCheck' 'services / Test / testOnly *SessionBindingRecoverySpec'`
  red-2 exit1:4executed/4failed before production/README edits. The prior red
  attempt was a fixture compile error (4 ambiguous references,0tests), corrected
  by the service test owner and honestly retained.
- Final requested format checks:
  `sbt -batch 'services / Test / scalafmtCheck' 'independentTests / Test / scalafmtCheck'`
  exit0; no rewrites.
- Targeted:
  `sbt -batch 'services / testOnly *' 'independentTests / Test / testOnly *AdversarialRuntime*'`
  exit0; services40/7suites + runtime18/3suites =58passed,0failed/canceled/ignored/pending.
- Full `/usr/bin/time -p sbt -batch check`: exit0,1,253 tests / 156 fresh reports,
  0failures/errors/skips; baseline1248+4module+1net independent=1253.
  Services40, independent665. Expected nested failure-probe self-test is not an
  outer failure; outer success/TestRunMarker verified. Raw full log:
  /tmp/phase11c-r1-full-check.log, 1723342bytes,
  SHA256 cd1d970fc3ba52792fc38af5f404bbb35d78540c9b12f28172d9d7e5dfabeccd.
  Full elapsed 724.18s. Other exact argv/env/exits/raw hashes: commands.json.
- Formatting disclosure: red-format and red-format-2 each rewrote only the new
  module suite; final-format rewrote only QueryService.scala and the HTTP spec.
  Owners authorized those rewrites. Both specialists stopped writing before gates.
  All 8 gate-start records were exclusive-created immediately before launch,
  never rewritten; final hashes/mtimes match. Final 25-file snapshot remained frozen.
- Current coverage20categories:51existing+33new cross-module=84 selected named
  tests, plus4 additional module regression cases. Runtime map21existing+18new=39;
  category16 existing2/new4/total6; category17 2/5/7. Historical maps unchanged;
  current map replaces the old permanent503 expectation and adds lost-reply HTTP.
  ExposedDefect0; no tag/exclusion/build-engineer needed. All mapped cases appear
  in fresh XML. Mutation checks6service+7independent are reasoning only.
- Evidence scripts exit0; git diff --check exit0.423 protected files and earlier
  evidence unchanged except append-only reports. No cloud/provider, nested
  delegation, reviewer, commit/push, human gate or further batch occurred.

Required repair acceptance:
R11C-1 High (formerly F11B-1), service-engineer + independent test-engineer:
- Fake body-binding update really applies the revision0 write, then returns
  Retried(1,Rejected("conditional-conflict")). Authoritative primary-read
  reconciliation proves this caller's intended revision+1/fingerprint/requestId/
  traceId/payload before scheduling. Unique bindingToken is internal opaque JSON;
  reused client IDs cannot let a losing caller claim another binder's row.
- Require one workflow execution,200 or202that completes, persisted SUCCEEDED/result,
  stored-result same-key replay without another run, different body409.
- Verify both module regression and independent actual HTTP→QueryService→real
  runtime workflow case. Count3 is a literal hand-derived fixture fact; verify
  exact accepted claim/audit as well as workflow and LLM counters1.
R11C-2 Medium (coupled), same owners:
- One clean rejection leaves an unbound revision0 row. Same-key replay competes
  for the existing CAS and completes once rather than remaining retryable503forever.
- Both direct-success and lost-winner-reply module concurrency cases use two
  QueryService instances sharing a store and identical client request/trace IDs.
  Force both CAS contenders to rendezvous and losing caller to read the winner's
  QUEUED snapshot before winner returns. Exactly one applied binding/workflow.
- Independent HTTP case must assert initial503with0workflow/model calls, then
  completing replay,2bind attempts/1apply, stored replay/no rerun and changed409.
R11C-5 Low, user-approved README:
- Document real recovery, binder ownership and lost replies accurately; do not
  claim a durable dispatcher. Already-bound process-death and persistent outage
  limitations remain.

Ownership map (exact precedence in docs/agents.md):
- service-engineer alone: modules/services/** production/module tests/README.
  Native /root/service_engineer_11c_r1 wrote these, then stopped.
- test-engineer alone: tests/**; native /root/test_engineer_11c_r1 modified only
  AdversarialRuntimeHttpSpec.scala after service writer stopped; no production edits.
- Coordinator /root: docs/agent-runs/** phase evidence assembly only; prior content
  preserved. Human owns gate/commit/acceptance/ratification records.
- domain-engineer modules/core/**; hadoop-engineer modules/hadoop/**;
  entity-resolution-engineer modules/entity-resolution/**; spark-engineer modules/spark/**;
  storage-engineer modules/storage/**; rag-engineer modules/rag/** and prompts/runtime/**,
  prompts/schemas/**. Each module owner owns its module-local tests.
- build-engineer build.sbt/project/**/format/packaging/ignore/generated marker;
  factory-engineer constitutional/.claude/** except marker/.mcp.json and reserved
  agent-map/evidence-template files. dataset-engineer datasets/**;
  infra-engineer infra/terraform/**,scripts/**,optional .github/workflows/**;
  deploy-engineer approved execution evidence; experiment-engineer experiments/**,
  load-tests/**; documentation-engineer README.md/docs/** outside reserved subtrees;
  incident-responder docs/incidents/**; dependency-updater approved value tokens only.
  Reviewer owns no implementation edits. Unlisted/orphan ownership is not inferred.

Carried items and limitations:
- R11C-3 Medium NONBLOCKING remains ORPHAN: 24 tracked file:/var/** stats/.crc outputs
  need a human-assigned writer before deletion/ignore work. No assignment/removal now.
- R11C-4 Low title-markup blocking mismatch (hadoop-engineer) and R11C-6 Low run-ledger
  CAS lost-reply observation (storage-engineer) untouched. R11C-6 downstream impact
  remains untraced. Do not confuse service binding repair with storage-wide CAS repair.
- F11B-3/F11B-4,11A N3,Phase9 NB1–NB10,Phase10 F7/F8/F10–F17 and earlier Phase5–8
  limits unchanged; see repairs.md and initial evidence/11c/carried-findings.md.
- Raw logs only in /tmp; exact model revision unavailable. Synthetic local fakes
  establish no live DynamoDB/AWS/provider/EMR/scale/cost/durable-dispatch guarantee.
  Initial reviewer did not read most40k main-code lines or the full datasets;
  reports were scan-level and course README summarized. Disclose remaining unread
  scope rather than treating initial APPROVE gates as comprehensive assurance.
- Live AWS/provider Phase 14, bounded EMR Phase 15, infrastructure Phase 12+ remain
  future gates. No optional OpenSearch/index/service/CI/coverage tooling added.
  Codex workflow deviation/instructor acceptance and human Phase 11 gate unverified.

Re-assess the WHOLE repository for regressions in this exact 12-point order:
1. Correctness and data loss.
2. Contract and schema drift.
3. Artifact ownership violations.
4. Security, secrets, IAM assumptions and injection risks.
5. Hadoop and Spark distribution mistakes.
6. Entity-resolution over-merging and unreported uncertainty.
7. Storage idempotency and provenance.
8. RAG grounding and unsupported claims.
9. API behavior and failure handling.
10. Tests that would pass even if the behavior were broken.
11. Documentation claims not supported by implementation.
12. Cost and cleanup risks.
The repair acceptance above must not narrow the whole-repository review.

Rules:
- READ-ONLY. Edit/create NOTHING. Run no builds/tests, AWS/provider calls,
  data mutations, commits/pushes or subagents. Do not read secrets (.env,
  credentials, private keys or secret directories). Safe read-only Git/file/
  hash/XML/JSON inspection is allowed.
- Verify every finding against actual current files, then report ALL confirmed
  findings in one pass. Give severity,path:line,concrete failure input,expected/
  actual behavior,evidence,impact,owning agent,acceptance check,blocking yes/no.
  Clearly label code-derived/unexecuted findings; do not invent reproduction.
- Check owner separation for every changed/new path, actual fault injection,
  hand-derived assertions/mutation sensitivity, stored replay and CAS ownership,
  no hidden failing/skipped cases, evidence/raw hashes/start barriers/source freeze,
  no hardcoded live resources/secrets and no unsupported claims.
- Distinguish blockers, nonblocking observations, accepted limits and later gates.
  Local passes do not constitute independent approval; do not repair anything yourself.

Return:
1 VERDICT: APPROVE or REQUEST_CHANGES for Subphase 11C repair round 1 batch 1.
2 Findings in the 12-point order, with all required fields. Explicitly disposition
  R11C-1/R11C-2/R11C-5 against current files/evidence; carried items retain owners.
3 Report fields from docs/agent-runs/README.md: STATUS,OWNER,WORK ORDER,
  FILES CREATED,FILES MODIFIED,COMMANDS RUN,TEST RESULTS,VALIDATION RESULTS,
  ASSUMPTIONS,RISKS,MANUAL ACTION REQUIRED,BLOCKED-ON OWNER,
  BLOCKED-ON EVIDENCE,NEXT GATE. State no reviewer builds/tests/files edited.
4 ONE fenced NEXT PROMPT for the coordinator:
  Append verdict VERBATIM under Subphase 11C repair round 1 in review.md, marked
  user-supplied external review, and append finding dispositions to repairs.md.
  If REQUEST_CHANGES, authorize only the next bounded blocking owner batch with
  explicit IDs/paths, Step 0, sequential/no nested delegation, affected/full JDK 17
  gates and immutable pre-launch records; then complete recheck handoff and STOP.
  If APPROVE, tell coordinator to confirm the user's 11C commit (ask/wait if not
  committed; no automatic commit/push), and tell user Phase 11 is ready for their
  own human-gate/commit records. Do not infer human acceptance or start/prepare
  another batch or Phase 12. R11C-3 ownership needs a separate human decision.
  Never launch a reviewer or write human-gate.md,commit.txt,approval/ratification
  records. Stop at the authorized handoff with a complete reviewer prompt as applicable.

You are the independent, read-only code reviewer for ScholarChain Phase 9,
Subphase 9A, initial review, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase9.md
   Sections 3–7 and Subphase 9A in Section 8. Retained plan snapshot:
   docs/agent-runs/phase-09/evidence/9a/plan-of-record.md.
   User answers override conflicting plan recommendations: read the complete verbatim
   docs/agent-runs/phase-09/evidence/9a/user-answers.md.
3. Course Phase 9 specification:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-9-implement-the-runtime-collaboration-analysis-agents
4. docs/agent-runs/phase-09/prompt.md, owner-report.md, test-report.md,
   repairs.md and evidence/9a/storage-interface-handoff.md, delegation.md,
   source-files.json, source-audit.json, commands.md, targeted-all-1-result.json,
   targeted-all-1-excerpts.log, loader-repair-targeted-1.log,
   check-1-result.json/check-1-excerpts.log and check-2-result.json/check-2-excerpts.log.
   Full raw logs remain local under the paths and hashes in the result records.

Checkpoint facts:
- STATUS: COMPLETE implementation/local9A gates; independent review pending.
- Branch: phase-9
- Subphase base SHA: 5fee9ffc607cf802e4aaddf4a261c21f1f232fec
- Current HEAD: 5fee9ffc607cf802e4aaddf4a261c21f1f232fec; no agent commit or push.
- Changed tracked files (8):
- modules/core/README.md
- modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/DomainValidation.scala
- modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/Records.scala
- modules/rag/README.md
- modules/storage/README.md
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/Phase6CacheLoader.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/StoragePorts.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageLoaderSpec.scala
- Untracked source/config/test/prompt files (23), plus coordinator packet:
- modules/core/src/main/resources/scholarchain.runtime-config.v1.json
- modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/RuntimeConfig.scala
- modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/RuntimeContracts.scala
- modules/core/src/test/resources/wire/runtime-query-options.json
- modules/core/src/test/resources/wire/runtime-typed-claim.json
- modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/RuntimeContractSpec.scala
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/QueryPlannerAgent.scala
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/ResearcherResolverAgent.scala
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/RuntimeLlm.scala
- modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/RuntimeSchemas.scala
- modules/rag/src/test/scala/edu/uic/cs441/scholarchain/rag/Runtime9ASpec.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/IndexedEvidenceBundleStore.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/RuntimeArtifacts.scala
- modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/fakes/RuntimeFakes.scala
- modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/RuntimeArtifactStorageSpec.scala
- prompts/runtime/planner-v1.md
- prompts/runtime/synthesis-v1.md
- prompts/schemas/answer-synthesis-v1.json
- prompts/schemas/query-plan-v1.json
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9AArtifactPipelineSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9AEvidenceSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9APlannerSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentRuntime9AResolverSpec.scala
- docs/agent-runs/phase-09/** (new coordinator packet; exact inventory in evidence/9a/files.json)
- All31 changed source/config/test/prompt hashes match the pre-final-gate snapshot.
  git diff --check exit0. Frozen existing wire examples remain unchanged.
- User answers: offline9A, Phase8C deferred to14C (do not claim wholePhase8 acceptance);
  Bedrock Converse forced named-tool output behind LlmClient, configured model/version/region
  us-east-2/temperature, existing dependency only, no live9A/9B calls; additive optional fields
  on existing records, no v2 hierarchy, new per-claim verdict mapped to legacy status retaining
  ABSTAINED; ObjectStore-backed read-only artifacts/fakes and evidence-item lookup, no new
  tables/GSIs; authoritative population filters before stored-window metric ranking with scope
  and truncation or Unsupported; cross-community-degree bridge default with qualifications,
  stored coauthor terminology, W==T not independent, repeated collaboration uses edge count;
  future deterministic verifier/template facts/no LLM verifier/retain rejected claims in audit;
  bounded path statuses, qualified partial answers and fail-closed required audit writes;
  fused default with graph/vector and evidence-only workflow contracts, deadlines fit sync;
  versioned expanded benchmark belongs9C, fault/injection broader suites11B, scripted offline
  tests do not establish live quality/injection resistance. Full answers are required reading.
- JDK: Homebrew17.0.20.1; all sbt commands used the mandated JAVA_HOME/PATH/SBT_OPTS.
- Exact commands and results (full attempts/environment in commands.md):
  * sbt -batch 'core / Test / testOnly *RuntimeContractSpec *SerializationContractSpec'
    initial exit0,17passed; a preceding sandbox boot-lock attempt exited1 before startup.
  * sbt -batch 'storage / testOnly *RuntimeArtifactStorageSpec'
    first exit1 testcompile; next two exit1 with4passed/7failed due invalid synthetic fixtures.
    Fixtures corrected; production validation retained.
  * sbt -batch 'rag / testOnly *Runtime9ASpec' 'independentTests / Test / testOnly *IndependentRuntime9APlannerSpec *IndependentRuntime9AResolverSpec *IndependentRuntime9AEvidenceSpec'
    exit1 overall: initial RAG17passed; independent testcompile generic wildcard fixed.
  * sbt -batch 'core / Test / testOnly *RuntimeContractSpec *SerializationContractSpec' 'storage / testOnly *RuntimeArtifactStorageSpec' 'rag / testOnly *Runtime9ASpec' 'independentTests / Test / testOnly *IndependentRuntime9A*'
    exit0:17+11+20+22=70passed,0failed; actual fresh G1 producer/export integration passed.
  * sbt -batch 'core / Compile / scalafmt' 'core / Test / scalafmt' 'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'rag / Compile / scalafmt' 'rag / Test / scalafmt' 'independentTests / Test / scalafmt'
    exit0.
  * /usr/bin/time -p sbt -batch check > /tmp/phase9a-check-1.log 2>&1
    exit1,724.36s: modules425passed, independent397passed/1failed. Existing loader test
    expected3writes; approved homonym alias makes4. Build verification not reached.
  * sbt -batch 'independentTests / Test / scalafmt' 'independentTests / Test / testOnly *IndependentStorageLoaderSpec'
    exit0:5passed,0failed. Test owner updated4write/replay expectations and explicitly
    checked new alias identity/confidence/source provenance; production unchanged.
  * /usr/bin/time -p sbt -batch check > /tmp/phase9a-check-2.log 2>&1
    exit0,705.87s:831passed,0failed; core169/Hadoop64/ER39/Spark38/storage62/RAG53/
    independent398/build8. The injected format-stage failure is the expected passing
    CheckFailurePathSpec; successful TestRunMarker ran at completion.
- Evidence paths: docs/agent-runs/phase-09/evidence/9a/; reviewer packet inventory files.json.
- Limitations/manual actions: bounded complete selected-table snapshots (defaults10,000rows/
  16MiB), larger exports fail closed; missing authoritative filter coverage returns Unsupported;
  conservative planner grammar rejects novel/unrepresentable phrasing; bounded JSON-Schema
  subset fails on unsupported keywords; filesystem prompt directory must be supplied; model/
  region/tool compatibility and live quality unverified; caller owns SDK region/IAM/lifecycle/
  disabled retries. Phase10 must assemble IndexedEvidenceBundleStore; existing bundles need
  replay for item indexes; identity caches need reload for unsuffixed homonym aliases. Index
  publication is not atomic across stores and failed writes return failure with retry support.
 9B retrieval/evidence/workflow stages and9C synthesis/verifier/audit execution/CLI/benchmark
  remain future scope. No live calls, infrastructure changes, human-gate edits or commits.
- Prior external findings/repair rounds: none; this is initial9A review. Integration repairs I1–I9
  are recorded in repairs.md with observed final passing evidence. All specialist agents completed;
  no builds/jobs remain running. No reviewer was launched.

Review rules:
- Read-only. Do not edit files, run builds or tests, call AWS/providers, change data, commit or
  push. Do not read secrets. Inspect git diff 5fee9ffc607cf802e4aaddf4a261c21f1f232fec
  plus all untracked files; report ALL confirmed findings in one pass.
- Check ownership against docs/agents.md and the user-approved9A storage prerequisites;
  no hardcoded resource/model/threshold values without config+rationale; no secrets in files,
  logs or evidence; reported results match retained logs; tests assert independent expectations;
  cloud/spend gates and lean scope respected.
- Check9A: backward-compatible optional payloads/frozen wire parsing, verdict mapping retaining
  ABSTAINED, exact numeric values, runtime config/deadline budgets; forced named-tool adapter
  and schema/version enforcement; allowlisted plans, constraint/metric preservation and bounded
  retry/fallback; ambiguity/notfound and DBLP suffix behavior; honest confidence/coauthor context;
  source-verified bounded real/fake artifacts, authoritative filter-before-ranking, qualifications,
  evidence-item lookup/collision/hash/partial-write behavior and truthful provenance.
- Future9B/C controls belong to later subphases: deterministic verifier as final decider,
  template-rendered facts, qualified interpretation, rejected claims retained in audit, untrusted
  semantic text and vector-only numeric abstention. Check contracts/prompts for compatibility,
  but do not demand later implementations now. Benchmark file/CLI/workflow are future scope.
- Distinguish blockers, nonblocking observations and unverified live/future gates. Independent
  tests authored by test-engineer are not a reviewer verdict. No self-approval is claimed.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase9A.
2. Findings: severity, path:line, evidence/reasoning, impact, owning agent, acceptance check,
   blocking yes/no. Include all confirmed findings in one pass.
3. Report fields from docs/agent-runs/README.md.
4. A complete NEXT PROMPT in one fenced code block that the user can paste:
   - APPROVE: instruct main agent to append this verdict verbatim to phase-09/review.md under
     Subphase9A, marked user-supplied external review; confirm the user committed9A (if not,
     ask and wait); start ONLY9B from the Drive plan after that gate, beginning Step0 questions;
     preserve all ten user decisions and deferred live8C; return next reviewer prompt per
     Section10 without invoking a reviewer; then stop. No9C preparation/implementation.
   - REQUEST-CHANGES: instruct main agent to append verdict verbatim to review.md and routed
     findings to repairs.md; fix ONLY listed blocking findings via owning agents; rerun affected
     targets and full JDK17 sbt check; do not start9B; return a complete recheck reviewer prompt
     without invoking a reviewer; stop. Nonblocking findings are listed but not required.

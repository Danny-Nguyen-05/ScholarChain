<!-- Course-named copy of owner-report.md in this folder, added in Phase 17 (package 17D, docs/agent-runs/phase-17/prompt.md). The text below this note is identical to owner-report.md, which is unchanged. -->

# Subphase 9A — contracts, storage prerequisites, prompts, planner and resolver

STATUS: COMPLETE

Implementation and local9A gates are complete. External review and human acceptance are pending.

OWNER: `/root` coordinator, phase evidence only. Native specialists: `/root/domain_engineer`
owns `modules/core/**`; `/root/storage_engineer` owns `modules/storage/**`;
`/root/rag_engineer` owns `modules/rag/**`, `prompts/runtime/**`, `prompts/schemas/**`;
`/root/test_engineer` owns `tests/**`. All inherited the session model; the exact deployed model
identifier is not exposed. No specialist delegated and no reviewer was launched.

WORK ORDER: Subphase9A only. Exact Drive plan snapshot and the ten user-supplied answers are
in `prompt.md`, with original snapshot/answers under `evidence/9a/`. Answers override conflicting
plan recommendations. Base/HEAD `5fee9ffc607cf802e4aaddf4a261c21f1f232fec`, clean initial tree
on phase-8, new branch phase-9. No commit/push. Phase8C remains deferred by design to Phase14C;
this is not acceptance of the entire Phase8. Human gate files were not created or modified.

FILES CREATED: Twenty-three source/config/test/prompt files, enumerated and hashed alongside
the eight modified files in `evidence/9a/source-files.json`; coordinator evidence/reports in
`docs/agent-runs/phase-09/**`. No new dependency, table, GSI, infrastructure, service or managed search/vector index.

FILES MODIFIED: Core README, Records.scala, DomainValidation.scala; RAG README;
storage README, Phase6CacheLoader.scala, StoragePorts.scala; existing independent
IndependentStorageLoaderSpec.scala (approved extra-alias count/provenance assertions). Existing frozen wire examples
were preserved. Mechanical scalafmt was centrally run after owners completed writes.

COMMANDS RUN: Exact JDK17 environment, sbt commands, exit codes and failed attempts in
`evidence/9a/commands.md`. Java17.0.20.1 Homebrew. Core targeted gate exit0;
storage first testcompile failed, then two11-test runs had4passed/7failed due invalid fixtures;
RAG initial17passed, independent testcompile initially failed on generic enum wildcard.
Repairs were routed to owners. Final combined target exit0:70passed0failed; formatter exit0.
Full check1 exit1 after724.36s: modules425passed, independent397passed/1failed
because an existing loader test still expected3writes instead of4 with the approved alias.
Test owner updated4write/replay expectations and added provenance checks; affected5/5passed.
Production source hashes unchanged. Final full check2 exit0:831passed0failed,705.87s wall;
core169/Hadoop64/ER39/Spark38/storage62/RAG53/independent398/build8. Expected
checkProbeInjectFailure is the passing build failure-path self-test, followed by successful marker.

TEST RESULTS: Final targeted core17/storage11/RAG20/independent22 passed. Twelve new core
cases plus five frozen-wire cases. Independent integration generated a fresh temporary G1
Phase6 export:10researchers,9works,18windowededges,28tables. It materialized the real runtime
artifact and checked literal metrics/rankings/support/qualifications. No retained target export
or live service was required. Final full gate passed all831 tests (see check-2-result.json/excerpts); all31 source hashes
remained unchanged from the pre-final-gate snapshot and git diff --check returned0.

VALIDATION RESULTS: Existing domain records gained defaulted optional runtime payloads.
Per-claim verdicts map to legacy statuses while retaining ABSTAINED. Decimal-string fields
preserve exact stored numbers. Audit contracts retain attempted/rejected claims. Config binds
model/version/region/temperature and validates the stage critical path against synchronous
deadline. Bedrock adapter forces exactly one named tool, uses injected SDK clients, bounds
requests/usage and sanitizes errors. Versioned schemas are executable through a fail-closed
documented subset validator. Planner preserves supported operations/metrics/constraints or
returns Unsupported; malformed output has one bounded retry then narrow fallback. Resolver
groups only canonical IDs, abstains on ambiguity/notfound, retains optional confidence and
bounded source-backed coauthors with truncation, and honors post-call deadline checks. JSON
stage outcomes carry query/plan correlation and run IDs without question/source payloads.

The six read-only artifact operations and exact signatures were published before coding
(`evidence/9a/storage-interface-handoff.md`). Source manifests/rows/hashes/lineage are verified
before bounded immutable ObjectStore publication and again on read. Ranking filters the
authoritative population before selecting exact stored values and discloses counts/truncation.
Stored bridge/community convergence/iterations and temporal presence are retained. Coauthor
support retains exact works/optional years. Immutable evidence-item pointers resolve through
IndexedEvidenceBundleStore.getItem without changing frozen ID formats or adding infrastructure.
The cache loader publishes source-backed unsuffixed DBLP homonym aliases without merging IDs.

ASSUMPTIONS: User answers1–10 are retained verbatim. Region us-east-2 is an example config
value; model ID/version remain explicit offline placeholders. Topic/venue population associations
span source-export authorship metadata, while metrics are from the requested stored window.
Missing associations are unknown metadata, not proof of no association. Stored coauthor fields
retain their meaning; future repeated-collaboration answers use edge jointPublicationCount.
Fixture provenance is synthetic direct Phase6 input, not an executed Hadoop/ER acquisition.

RISKS: Independent review pending. Conservative planner grammar rejects novel phrasing/unsupported
constraints; fallback requires its documented anchored forms. JSON Schema validator supports
only the checked-in keyword subset and fails on unknown keywords; it is not a general schema
engine. Runtime assets currently use an explicit filesystem prompts directory. Caller owns SDK
region/IAM/lifecycle and disabled SDK retries. Model/tool/region compatibility, real retrieval
quality and live injection resistance remain unverified. Artifact snapshots are bounded complete
selected-table snapshots (defaults10,000rows/16MiB), not a scalable partitioned index; oversized
exports fail closed. Missing filter coverage fails Unsupported. Bundle/index publication is not
atomic: a failed required pointer write can leave a bundle, returns failure, and is retryable.
Optional OpenSearch, extra indexes/services and CI are omitted per lean scope.

MANUAL ACTION REQUIRED: User launches the supplied read-only reviewer; only the user commits.
Phase10 composition must wrap its bundle store in IndexedEvidenceBundleStore; existing bundles
need replay through the wrapper to index item IDs. Existing entity caches need idempotent
source reload to acquire unsuffixed homonym aliases. No live9A/9B calls are authorized, and
the optional9C smoke requires separate written approval/dollar cap. User owns any interim
Phase8 human gate and later Phase9 acceptance/commit evidence.

BLOCKED-ON OWNER: None for implementation/local validation. External review and human
acceptance remain separate gates.

BLOCKED-ON EVIDENCE: None for local9A gates. All live/provider evidence is intentionally
unverified. No independent review verdict exists for9A yet.

NEXT GATE: User-launched independent read-only9A review using evidence/9a/reviewer-prompt.md;
then the user decides on commit. Coordinator has stopped; no builds/jobs/specialists remain running.
9B retrieval/workflow and9C synthesis/verifier/audit execution/CLI/versioned benchmarks remain
future work. Evidence-only and retrieval modes are contracts in9A, not completed workflows.


# Subphase 9A — repair round 1 (B1–B4)

STATUS: COMPLETE
Local implementation and validation complete; user-launched independent recheck pending.
OWNER: /root coordinator assembles evidence; /root/domain_engineer core B2 contracts;
/root/rag_engineer B1/B2/B3 resolver; /root/storage_engineer B3/B4; /root/test_engineer
independent B1–B3 regressions. Exact native/path routing: evidence/9a-r1/delegation.md.
WORK ORDER: User supplied REQUEST-CHANGES and instructed "Fix all blockings for me".
B4 selected FIX NOW. No additional questions. Only B1–B4; N1–N7 logged/deferred.
Original10decisions and Phase8C→14C deferral preserved. Same uncommitted9A tree on phase-9,
base/HEAD5fee9ffc607cf802e4aaddf4a261c21f1f232fec. No commit/push or human-gate edit.
FILES CREATED: Runtime9ARepairSpec.scala plus IndependentRuntime9ARepairPlannerSpec.scala
and IndependentRuntime9ARepairResolverSpec.scala; coordinator evidence under evidence/9a-r1/.
FILES MODIFIED:13prior source/config/test/doc files; exact before/after delta16paths in
repair-files.json, cumulative34source/config/test/prompt paths+hashes in source-files.json.
COMMANDS RUN: Exact JDK17 environment/commands/exit codes in evidence/9a-r1/commands.md.
Coretarget1 exit0;storagetarget1 exit0;independenttarget1 exit0;RAGtarget1 testcompile exit1
(helper name/default-getter collision), test-only rename then RAGtarget2/formatting exit0.
Full /usr/bin/time -p sbt -batch check exit0;725.07s wall,901passed0failed.
Raw log hash/excerpts in check-1-result.json/check-1-excerpts.log.
TEST RESULTS:140targetedpassed0failed: core21/storage15/RAG40/independent64. Includes42new
independent cases,20new module repair cases,4core cases and4storage cases. Existing frozen
wire cases and fresh actualG1 artifact pipeline still pass. RAG testcompile failure retained;
production source unchanged during its fix. Full901passed0failed: core173/Hadoop64/ER39/
Spark38/storage66/RAG73/independent440/build8; expected injected failure self-test passed.
All34source hashes unchanged since pre-final-gate; git diff --check exit0.
VALIDATION RESULTS: B1 derives metric/measure/operation, exact window/comparison vectors and
explicit author conversion from request semantics independently of model fields; disagreeing
schema-valid outputs retry then safe fallback/Unsupported. Unspecified bridge/default window
use configuration, explicit participation cannot default away, since2015 cannot narrow to
2015-2019, extra comparison windows and unrequested conversions reject. Source order retained
for explicit multi-window comparisons. Tests include positivefirst-call and negative alternatives.
B2 groups valid cache rows by canonicalID before the dedicated configured cap. Candidate
provenance lists have configured caps and exact distinct totals/truncation; confidence aggregation
uses all source rows. Overflow returns bounded Ambiguous with totalCandidateCount/truncated,
never a raw-row-bound failure. B3 actual artifact fake returns Missing for known identity absent
in stored window; resolver keeps Resolved/Ambiguous candidates. Undeclared window rejects.
B4 successful immutable pointer load caches parsed/verified indexed data per reader instance;
concurrent cold reads share oneGET, warm reads bypass GET/reparse/revalidation. Failed loads
are retryable; first corruption still rejects. Keyed maps eliminate repeated global association
scans and quadratic edge/support binding. Tests establish structural reuse, not production latency.
ASSUMPTIONS: Immutable SHA-bound pointer is the cache authority; a different pointer requires a
new adapter. Per-candidate totals count distinct merged cache/context values before clipping.
No scored identity confidence is invented. Bounds are explicit configuration with rationale.
RISKS: Independent recheck pending. N1–N7 remain open/deferred unchanged,
including port-level context references bounded only by snapshot, conservative filter coverage,
shared maxInputBytes, live-region check, real confidenceNone and fixed-v1 asset paths. Existing
bounded snapshot/memory, conservative planner grammar and unverified live quality limits remain.
MANUAL ACTION REQUIRED: After local gates user launches read-only repair recheck, then decides
commit. No live approval exists. Existing Phase10 indexed-store assembly and cache/bundle reload
requirements remain; no9B work begins from this repair session.
BLOCKED-ON OWNER: None for implementation/local validation.
BLOCKED-ON EVIDENCE: None for local repair gates. User-launched independent recheck pending;
all live/future gates remain unverified.
NEXT GATE: User-launched read-only repair recheck using evidence/9a-r1/reviewer-prompt.md,
then user commit decision. All specialists/builds completed. Coordinator stopped; no9B work.


# Subphase 9A repair round 1 — external approval recorded / awaiting user commit

STATUS: COMPLETE evidence recording; user commit gate pending.
OWNER: /root coordinator, phase evidence only.
WORK ORDER: User supplied repair-round-1 APPROVE and NEXT PROMPT StepA/B.
FILES CREATED: evidence/9a-r1/external-recheck.txt, external-recheck.sha256,
commit-gate-observation.json.
FILES MODIFIED: review.md (verbatim review and dated append-only N9 clarification),
repairs.md (B1–B4 external FIXED; N8/N9 OPEN/nonblocking), this report and test-report.md.
COMMANDS RUN: Read-only git status/branch/rev-parse/log; source hash verification34/34;
git diff --check exit0. Coordinator evidence writes only; no staging/commit/push.
TEST RESULTS: No rerun for evidence-only recording. External reviewer verified retained140
 targeted/901full passes and raw-log bindings; all34source hashes still unchanged.
VALIDATION RESULTS: Independent APPROVE recorded verbatim; prior reviews/opening preserved.
N8/N9 carried forward beside N1–N7. Current branchphase-9 HEAD5fee9ffc607cf802e4aaddf4a261c21f1f232fec;
repaired9A remains uncommitted. No9B files read for implementation, authored or prepared.
ASSUMPTIONS: Independent code approval is not a user commit or human-gate acceptance.
RISKS: Existing live/future gates and N1–N9 deferrals remain.
MANUAL ACTION REQUIRED: User commits repaired9A and supplies SHA before9B Step0, per user NEXT PROMPT StepB.
BLOCKED-ON OWNER: User for commit gate only.
BLOCKED-ON EVIDENCE: User-supplied9A commit SHA; no code blocker remains.
NEXT GATE: Wait for user commit confirmation/SHA. Then record9B base and ask9B Step0 questions.


## 2026-10-26 — user-authorized commit and push

User explicitly instructed: "can you commit and push them for me". This supersedes the
work-order default that agents must not commit/push, for the reviewed9A tree only.
Coordinator verified branchphase-9, HEAD5fee9ffc607cf802e4aaddf4a261c21f1f232fec,
all34reviewed source hashes unchanged, git diff --check exit0, no staged prior changes
and no out-of-scope pending paths. Retained full gate901passed0failed remains applicable;
no source edits or extra test run were needed for evidence-only approval recording.
Lean test logs/excerpts under phase-09/evidence are included explicitly despite global
*.log ignore rules. Full raw /tmp logs, datasets, generated targets and credentials are
excluded. No human-gate.md/commit.txt is authored. Commit/push results will be reported
from actual git output; this entry does not claim an unobserved commit or push.

Commit packaging note: three compiler-log display copies had trailing spaces trimmed;
original raw /tmp bytes preserved, transformations SHA-bound in evidence/9a-r1/commit-log-normalization.json.


# Subphase 9B — implementation and local validation complete

STATUS: COMPLETE for9B implementation/local gates; user-launched external review pending.
OWNER: /root coordinator; /root/domain_9b modules/core/**, /root/rag_9b modules/rag/** and owned prompts, /root/tests_9b tests/**. Native IDs/territories in evidence/9b/delegation.md.
WORK ORDER: User requested9B after approved9A commit f139f9c925b4925864a2c9a33734d869a1929cd2, then answered "use all recommend defaults". Branch phase-9; HEAD/base unchanged. Initial tree clean. All original ten decisions retained;9B only.
FILES CREATED:17source/test files plus lean evidence/9b/. Exact22source/test/module-documentation paths+SHA256 in source-files.json; complete changed/untracked inventory in files.json.
FILES MODIFIED:5existing source/test/module-README paths plus coordinator prompt.md, repairs.md, owner-report.md and test-report.md. No human-owned decisions or gates changed.
COMMANDS RUN: Exact JDK17 environment/commands/exits in evidence/9b/commands.md. java-version reports Homebrew17.0.20.1. Final coretarget2 exit0; final integratedtarget4 exit0; touched-project scalafmt applied. /usr/bin/time -p sbt -batch check exit0,707.18seconds. git diff --check exit0; all22source hashes and29unchanged prior reviewed9A paths verified. Full raw /tmp/phase9b-check-1.log SHA256 4a3835389a36c942220ca8650876b04d2b8e69087f8a1b8522bb3fd670077fea.
TEST RESULTS:135targeted passes/0failures:core39/storage15/RAG15/independent66. Full1001passed0failed:core196/Hadoop64/ER39/Spark38/storage66/RAG88/independent502/build8. Expected injected format-stage failure is the passing build self-test; final TestRunMarker ran. Earlier testcompile name collision, default-path context overrun and invalid new temporal fixture are retained with raw hashes/excerpts and routed repair evidence. No failing assertion removed or production validation weakened.
VALIDATION RESULTS: Six9B stages/workflow implemented against injected ports; exact stored metrics and authoritative population filtering; bounded component-qualified paths and full hop supports; community/bridge/temporal source qualifiers; verified descriptive semantic retrieval and model/filter checks; JSON data delimiting; stable complete-content-bound item IDs and indexed persistence; resolved identity names/confidence/provenance retained; conservative context+byte budgets, atomic path/comparison groups and disclosed ranking prefixes; graph/vector/fused/evidence-only modes; essential-vs-optional failures, parallel fanout, completion-time deadlines and cancellation. N1 actual-item partition gap addressed. Two further required evidence contract gaps are additive/defaulted, no v2 hierarchy. Frozen wire examples/planner grammar unchanged. No storage/build/infrastructure change required.
ASSUMPTIONS: Original G1 ten researchers/nine canonical works/nine all-years edges retained; community partition, metadata and DBLP homonyms are declared synthetic overlays. Filter values identify authoritative stored metadata; no invented free-text-to-ID mapping. JVM adapters honor interruption or own timeouts.
RISKS: External review pending. Strict metadata coverage can make real filters Unsupported; larger essential groups can abstain. Context budget uses conservative UTF8byte upper bound; maxInputBytes shared16KiB remains N3. Live provider/model/tool/region/temperature compatibility, live quality/injection resistance, cloud scale/cost and production latency unverified. N2-N9 carried forward, N8 deferred9C unless needed; confidenceNone disclosed. Phase8C remains deferred14C with no whole-Phase8 acceptance claim. Full limitations in evidence/9b/limitations.md.
MANUAL ACTION REQUIRED: User launches independent read-only9B reviewer with evidence/9b/reviewer-prompt.md. Commit/push requires later explicit user instruction after review. User owns Phase8 interim gate and all human-gate/commit records. No live approval exists.
BLOCKED-ON OWNER: None for implementation/local validation.
BLOCKED-ON EVIDENCE: Independent user-launched external review; live/future gates remain unverified.
NEXT GATE: User-launched9B read-only review. All three specialists completed; build finished. No reviewer, nested delegation, live/cloud/provider call, commit/push, human-gate edit or9C implementation/preparation occurred. Stop at9B.


# Subphase 9B repair round 1

STATUS: COMPLETE implementation and local validation; external recheck pending.
OWNER: /root coordinator evidence/gates; /root/rag_9b_r1 modules/rag/**; /root/tests_9b_r1 tests/**.
WORK ORDER: User "fix all blocking bugs for me" on external9B REQUEST-CHANGES. Only B1 blocking; O1-O10 log only. Base/HEAD f139f9c925b4925864a2c9a33734d869a1929cd2, branchphase-9; prior9B uncommitted. Original10decisions/9Bdefaults binding; no questions for repair.
FILES CREATED: Lean evidence/9b-r1 records only; no newsource files.
FILES MODIFIED: Four reviewed9B paths: CollaborationMetricsAgent.scala, Runtime9BSpec.scala, modules/rag/README.md, IndependentRuntime9BStagesSpec.scala. Coordinator appended review.md verbatim externalreview+NEXT PROMPT, prompt.md, repairs.md and owner/test reports. Exact four before/after hashes repair-files.json; cumulative22source hashes source-files.json.
COMMANDS RUN: Required JDK17environment/java-version and exactformat/target/fullcommands in evidence/9b-r1/commands.md. Target1 exit0,99passed0failed,11.66seconds. Full /usr/bin/time -p sbt -batch check exit0,1004passed0failed,717.84seconds. git diff --check exit0; sourcehashes verified afterfullgate. No failedbuild/testattempt in repairround. Raw full /tmp/phase9b-r1-check-1.log SHA256 6b4755d9be0c7449f27d1d4ace7c1942bd6728a0b39f7935823e5a8f373ef42a.
TEST RESULTS: Targetstorage15/RAG17/independent67=99passed0failed. Fullcore196/Hadoop64/ER39/Spark38/storage66/RAG90/independent503/build8=1004passed0failed. Expectedinjectedformatfailure is passingbuildselftest; finalTestRunMarker observed. Added2modulecases and1independentcase; existingindependentP90case strengthened. Default4hop/rankingworkflows pass unchanged.
VALIDATION RESULTS: Exact metric evidence remains approximate=false, samecompleteitem with/withoutestimate, and named/ranking exactfields agree. Separate deterministic distance-estimate item approximate=true contains component/P90=4.0/methodsampled-bfs/window/run and specific sourcefieldrefs, content-bound by existinghelper. Existingbuilder nonrankingadmission unchanged/atomic: exact-only budget refuses pair beforewrite; fullpair persists and itemlookup resolves. Iteration-limited labels retained. N1 remainsfixed. O1-O10 loggedunchanged; N2-N9 carriedforward. No domain/storage/build/infra/buildercontracts changed. All18unrepaired9B paths and29unchangedprior9A paths match reviewedhashes; originalwire/planner unchanged.
ASSUMPTIONS: Stored PathLengthEstimate sourcevalidation supplies component/window/run integrity; no metrics recalculated. Tests use declared syntheticfixtures, notlivequality/performance evidence.
RISKS: External recheckpending. O1-O10 remainknownnonblockers perreview, including convergencequalifier scope/mixedprovenance/semanticidentity andcontextlimits. Liveprovider/model/region/injection/latency/realcoverage unverified. Phase8C deferred14C, no wholePhase8acceptance. All9Cwork untouched.
MANUAL ACTION REQUIRED: Userlaunches read-only repairrecheck using evidence/9b-r1/reviewer-prompt.md; nocommit9B untilapproved. Userownshumangates; no liveapprovalexists.
BLOCKED-ON OWNER: None forimplementation/localvalidation.
BLOCKED-ON EVIDENCE: User-launched externalrecheck, plus laterlive/futuregates.
NEXT GATE: Independentread-only9Brepairround1 recheck. Allspecialists/buildscompleted; no nesteddelegation/reviewer/livecalls/commits/pushes/humangateedits or9Cwork. Stop.


# Subphase 9B repair round 1 — external approval recorded

STATUS: COMPLETE approval recording; waiting at the user commit gate.
OWNER: /root coordinator, phase evidence only.
WORK ORDER: User supplied independent APPROVE and directed approval recording followed by a commit gate.
FILES CREATED: evidence/9b-r1/external-recheck.txt, external-recheck.sha256, commit-gate-observation.json.
FILES MODIFIED: review.md (verbatim append), repairs.md (external B1 closure, R1/R2 logged), this report and test-report.md.
COMMANDS RUN: Read-only git status, branch, log -1, rev-parse; compared all 22 source hashes to the working tree and HEAD; git diff --check. No staging, commit or push.
TEST RESULTS: No rerun for evidence-only recording. Retained targeted 99 passed and full 1004 passed, zero failed; independent reviewer verified the evidence. All 22 source hashes remain unchanged.
VALIDATION RESULTS: APPROVE recorded verbatim, including the supplied next prompt, which ends mid-sentence. Earlier review text and human decisions remain intact. B1 externally fixed; R1/R2 and O1–O10 logged as nonblocking. Approved 9B changes remain uncommitted on phase-9 at f139f9c925b4925864a2c9a33734d869a1929cd2.
ASSUMPTIONS: Independent code approval does not itself authorize an agent commit or push.
RISKS: Existing nonblocking and live/future gates remain open. Phase 8C stays deferred to 14C.
MANUAL ACTION REQUIRED: User commits approved 9B or explicitly instructs the agent to commit it.
BLOCKED-ON OWNER: User for the commit gate only.
BLOCKED-ON EVIDENCE: Approved 9B commit SHA.
NEXT GATE: Wait for commit authorization/confirmation. No 9C files, questions or implementation prepared.


## User-authorized 9B commit and push

The user explicitly instructed: "yes please commit and push it". This authorizes committing
and pushing the independently approved 9B work and repair round 1. The coordinator verified
all 22 reviewed source hashes, an empty prior index, expected ownership/path scope and a clean
git diff --check. Retained full validation remains 1,004 passed and zero failed; no source
changes or test rerun were needed for approval recording. Lean evidence packets are included;
full raw /tmp logs and generated outputs remain excluded. No human-gate or commit record is
written. Commit and push results will be reported from observed Git output. No 9C work starts.


# Subphase 9C

STATUS: COMPLETE implementation and local validation; user-launched independent review pending.
OWNER: /root coordinator for evidence and serialized gates; /root/domain_9c core contract gaps; /root/storage_9c storage contract gap; /root/rag_9c RAG; /root/tests_9c independent tests. No nested delegation or reviewer launch.
WORK ORDER: Implement only 9C with all seven user-approved defaults, ten original decisions and approved 9B defaults. Branch phase-9; base and HEAD 2527de01252286080e6db776b9cc0199a9353e1e. Initial tree was clean and all 22 approved 9B committed source blobs were verified.
FILES CREATED: Eighteen new source/test/resource files and lean evidence/9c packet. Runtime synthesis/verifier/audited workflow/offline fixture/CLI/benchmark; audit validation/storage adapters and feature suites. Exact paths, owners and hashes: source-files.json, change-files.json and files.json.
FILES MODIFIED: Twenty existing source/test/module-doc paths, plus phase-09 prompt, repairs, owner and test reports. Core/storage changes are approved contract gaps only. Existing prompts/schemas are reused and remain unchanged. Frozen wire examples, build, services, infrastructure, constitutional files, prior reviews, user decisions and human gates remain unchanged.
COMMANDS RUN: Required JDK 17 environment for every sbt invocation; Homebrew 17.0.20.1 recorded. Exact commands/redirects/exit codes/counts/raw paths and SHA-256 are in evidence/9c/commands.md and *-result.json. Core targeted: exit 0, 50 passed. Final formatted targeted selection: exit 0, storage 14/RAG 74/independent 211 = 299 passed, 16.31 seconds. Actual CLI benchmark rerun: exit 0, 15/15 passed. Full /usr/bin/time -p sbt -batch check: exit 0, 1,131 passed, zero failed, 780.69 seconds. git diff --check and untracked-file whitespace checks are recorded in final-validation.json.
TEST RESULTS: Full counts core 207/Hadoop 64/entity-resolution 39/Spark 38/storage 80/RAG 107/independent 588/build 8 = 1,131. Final TestRunMarker observed; injected format-stage failure is the expected passing build self-test. New 9C cases: core 11, storage 14, RAG 17, independent 85 = 127 beyond the approved 1,004 baseline. Every failed attempt is retained; full check 1 was intentionally terminated (exit 143) after packet inspection found a discarded ambiguity candidate list. Owners fixed it, strengthened assertions, and reran targeted/CLI/full. No failing assertion was deleted.
VALIDATION RESULTS: Schema-validated typed synthesis and bounded retry/bytes; deterministic verification/templates and rejected-claim retention; exact decimals and evidence/identity/window/path checks; per-field convergence/approximation disclosure; source provenance distinct from request lineage; named semantic scope and trusted identity partition; deterministic evidence excludes prose; required audit fail-closed storage/readback/hash and deadline reservation; evidence-only synthesis bypass; 15 hand-derived benchmark cases with actual component/coauthor/path/community assertions and ranking-scope disclosures. Ambiguous terminal results retain both unselected homonym candidates and their bounded disclosure; audit resolved identities remain empty. All 38 final source hashes match after the full check. Nine unchanged prior 9B paths match reviewed hashes; 24 prior 9A paths untouched in 9C match the committed base.
ASSUMPTIONS: Synthetic G1 community/metadata/temporal/homonym overlays are disclosed; literal expected facts are hand-derived. Injected ports honor interruption or own deadlines. Audit session pointers have no expiry.
RISKS: External review pending. Live model/tool/region/temperature compatibility, live quality and general injection resistance, production latency and real enrichment coverage remain unverified. Interpretation/planner coverage is conservative; large atomic groups can abstain. Existing N/O/R observations and their exact dispositions are in coverage-and-limitations.md. P90 component evidence retains RESEARCHER_PROFILE type with typed distance-estimate kind. Broader injection/fault suites remain Phase 11B. Phase 8C remains deferred to 14C; no whole-Phase-8 acceptance.
MANUAL ACTION REQUIRED: User launches the read-only reviewer using evidence/9c/reviewer-prompt.md. User owns human-gate/commit records, Phase 8 interim gate and later commit authorization. No live smoke approval exists. Phase 9 closes only after external review and the user's human gate.
BLOCKED-ON OWNER: None for implementation or local validation.
BLOCKED-ON EVIDENCE: Independent external review and future live gates only.
NEXT GATE: User-launched read-only 9C review. Specialists and builds are complete. No commits/pushes, cloud/provider calls, secret reads, infrastructure/human-gate edits or Phase 10 work. Stop at 9C.


## Subphase 9C — external approval recorded

The user-supplied independent review returned APPROVE for Subphase 9C with no blocking findings. The complete review is appended verbatim in review.md. NB1–NB10 are logged in repairs.md with their exact owners, locations and acceptance checks; all are logged; not implemented.

All 38 reviewed source SHA-256 hashes still match evidence/9c/source-files.json. No source, test, build, infrastructure or evidence-result changes and no test reruns were made while recording approval. Retained results remain full check 1,131 passed / 0 failed, targeted 299 / 0, CLI benchmark 15 / 15.

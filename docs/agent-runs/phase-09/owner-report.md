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

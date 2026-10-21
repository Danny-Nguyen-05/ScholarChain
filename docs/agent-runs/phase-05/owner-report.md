Current checkpoint: **5B B1/B2 repair verification complete; external recheck pending.** Fresh gate: 356 tests passed on 174 unchanged frozen files. Earlier status entries below are historical.

Current checkpoint (2026-10-16): **5B implementation and technical verification complete; external review pending.** Fresh full gate: 339 tests passed on 170 unchanged frozen files. See the final 5B section below; earlier entries are historical.

# Phase 5 owner report

Current checkpoint:5A B2/N10repair and fresh257testverification complete; user-run externalrecheck pending. B1wasindependentlyclosed; earlierhandoffs/results preservedashistory. Lateststatus at end.

## Subphase 5A — contract and data readiness

STATUS: COMPLETE — 5A contracts, examples, data-readiness assessment and observed verification complete. External review/checkpoint acceptance pending; no Phase 5 acceptance inferred.
OWNER: `/root`, coordinator assembling explicitly launched native specialist reports.
WORK ORDER: Complete 5A only under prompt.md; user refinements are distributed systems/data engineering, 40 development plus 200 held-out real human reviews, repository material as current baseline, and ER-owner participation in contract agreement. Original external plan is reproduced verbatim in prompt.md. Starting snapshot: baseline.json.
FILES CREATED: Three core production contract/validation files, two owner test files, six core wire fixtures, ER README and four design-only JSON examples, one independent contract suite, and coordinator phase-05 evidence listed in review-inventory.json at handoff.
FILES MODIFIED: build.sbt (one dependency declaration), modules/core/README.md (additive contract documentation). Existing source records, StableIds, schema/config files, preparation features and accepted dataset samples are unchanged.
COMMANDS RUN: Initial `git status --porcelain=v1`, `git branch --show-current`, `git rev-parse HEAD`, `git log -1 --format=%s`, required instruction/plan/source reads. Initial status empty; branch main; HEAD 099e303311be7a1b2e2cf5655e0c7ce9fa710474. Exact verification commands/results and failed attempts are in test-report.md; source/evidence inventory is in review-inventory.json.
TEST RESULTS: Core targeted9/9 and independent targeted7/7 passed; six Scala wire roundtrips passed. Fresh sbt check exit0:236tests passed (core108,Hadoop64,independent60,build4), zero failures/errors/skips. Existing6Python tests,4sample checksums and manifest validation passed. Historical Phase4 counts are not used as new verification.
VALIDATION RESULTS: Owners agreed interfaces before implementation. data-readiness.json retains completed-run inspection: both final real sample runs have exact 34-part export inventories, matching lengths/SHA-256, run-ID agreement and nine job success markers. No new source data or labels acquired.
ASSUMPTIONS: Native inherited runtime models; no model override was requested, and exact opaque model revision is not exposed by the native delegation result. Canonical task identifiers below are the actual tool-returned identifiers; no numerical agent IDs or external reviewer IDs invented.
RISKS: Existing samples are insufficient for the requested 240 reviews; future acquisition is specified below. Validators check supplied structure and source binding, not external factual identity, evidence authenticity, score calibration, exporter completeness or model accuracy. A complete constraint bundle must be bound by the future run/export manifest to its content hash, run, input population and policy before downstream grouping.
MANUAL ACTION REQUIRED: User runs the independent read-only 5A review prompt and returns the full verdict. A returned APPROVE still needs explicit authorization before 5B. No labels/provider choice requested at this checkpoint.
BLOCKED-ON OWNER: User-selected external reviewer / user for checkpoint review.
BLOCKED-ON EVIDENCE: External5A verdict pending. No current technical verification blocker remains; data acquisition/labels/provider/evaluation are later-scope gates.
NEXT GATE: User runs reviewer-prompt.txt and returns full verdict. All workers/builds stopped. Begin5B only after returned review and explicit user authorization. No commits, pushes, AWS actions, live model calls or source acquisition performed.

### Native ownership and dependency handoffs

| Native task identifier | Role / exact write territory | Ready inputs, handoff and boundary |
| --- | --- | --- |
| /root/phase5a_domain | domain-engineer; modules/core/** | Inventoried existing contracts, waited for ER agreement/coordinator approval, added only shared contracts/context validation/tests/examples; formatted/tested own files, then froze. No matching/pair generation/group construction. |
| /root/phase5a_build | build-engineer; build.sbt/project/**/.gitignore | Independent initial lane. Changed only independentTests.dependsOn to include entityResolution. Existing gate and ignore rules sufficient; handed classpath verification to tester and stopped. |
| /root/phase5a_dataset | dataset-engineer; read-only inventory/design | Independent initial lane; no writes. Returned measured source/pair supply and future acquisition/partition bounds. Expanded acquisition remains5C. |
| /root/phase5a_er | entity-resolution-engineer; modules/entity-resolution/** | Started after build slot freed; agreed APIs directly with domain before writes, then produced local policy/config/sampling/label design examples and README. Consumed finalized domain fixture IDs, then froze. No runtime implementation. |
| /root/phase5a_test | independent test-engineer; tests/** | Started after dataset slot freed. Waited for finalized domain API before separate tests. Installs existing pinned Python verification requirement only in /tmp; exclusively runs independent/full checks after prior sbt slot exits. No production edits or review verdict. |

Coordinator plus at most three specialists were active concurrently. All workers were prohibited from delegation, secret inspection, later-subphase implementation and human decision edits. No code reviewer was launched or selected. No phase constitutional files changed. Human Phase1 and Phase4 decisions were read, not rewritten.

### Agreed shared contracts and concrete examples

New shared source files are ResolutionContracts.scala, ResolutionValidationContext.scala and ResolutionValidation.scala under the core Scala package. Their schema is scholarchain.resolution.v1; historical scholarchain.domain.v1 remains unchanged.

- Endpoints distinguish a work observation, parent-work author mention, ORCID profile and actual ORCID work activity. Identity uses full source/native-record/snapshot references. Work activities have no manufactured author list; nonwork activities require explicit unsupported-type diagnostics in5B, distinct from missing references.
- Canonical unordered pairs hash versioned compact JSON identity tuples. Block repetition/reversal cannot create new pair identities. Preferred work IDs bind to source context, not source-observation identity.
- Decision audit wraps unchanged MatchDecision with source-bound pair IDs, contributing candidate/block refs, feature availability/evidence, final path, confidence semantics, policy/config/input hashes and UTC timestamp. Model-reported confidence is separate from any system score. Missing scores require an explicit reason and a documented legacy numeric placeholder, never a fabricated measured score.
- Adjudication metadata exists iff final path is LlmAdjudicated; it preserves unresolved pre-adjudication outcome/score/path. An LLM final outcome cannot be CONFLICT. Actual eligibility/bands/provider JSON/cache behavior remain5B.
- Accepted links bind actual accepted audits. Complete grouping constraints carry explicit coverage even for no-ID members, cannot-links and authoritative-ID assertions. Bounded caller-supplied component validation rejects conflicts and missing coverage; no group construction/representative assignment occurs.
- Core only structurally validates candidate/evidence refs. The5B input bridge must validate their actual existence, hashes and relationship to each comparison.

Concrete fixtures in modules/core/src/test/resources/wire/: resolution-work-pair.json, resolution-researcher-pair.json, resolution-work-decision.json, resolution-researcher-decision.json, resolution-accepted-link.json, resolution-grouping-constraints.json. Nine owner tests and the independent suite validate their contracts; synthetic outcomes/scores/grouping assertions do not represent real matching or human labels.

Work example pair: resolution-pair:1b7b4ccf905e261f162fd9167241ae2acb6c6379821f225322dea43c82b1fff6.
Researcher example pair: resolution-pair:32c83838c7bcf409215f65a5e256dd8535fe0e7bdbef5f9aa28f469d07d06138.

ER-owned contracts/*.example.v1.json are explicitly DESIGN_ONLY, not accepted runtime inputs. They propose separate work/researcher policies, a sole effective policy that supersedes shared ER placeholders, disabled mode with zero live allowances, grouped sampling and synthetic label revisions bound to the real fixture pair IDs. CLI, scorer, normalization/features, provider seam, queue/UI/importer/evaluator remain unimplemented. Full numeric policy calibration and runtime canonicalization/strict schemas wait for their authorized subphase.

### Dataset inventory: measured current supply

Input bytes contain3 DBLP publications,1 OpenAlex work,1 Crossref work and1 ORCID profile. Each completed run exports5 work observations,10 author mentions,1 profile,16 activities and40 candidate block rows. Canonical full observation-pair dedup yields14 pairs:

| Endpoint kinds | Distinct pairs |
| --- | ---: |
| Work/work |6|
| ORCID work activity/work |3|
| ORCID profile/work |3|
| ORCID employment/work |1|
| ORCID distinction/distinction |1|

Of the six work/work pairs, three compare source copies of one DOI and three compare different DBLP publications sharing a venue. The three source-copy comparisons account for23 repeated block rows. Repeated mention names occur across copies of the same publication, with no observed repeated author across different works in this current population. Phase4 supplies no produced researcher identity pair stream; possible future mention alignment is not counted as actual eligible/human-reviewed supply. Current pair-connected material cannot provide independent development and held-out groups. Two processing invocations add no population diversity. Original source year disagreement is preserved.

### Future5C bounded acquisition proposal — unexecuted

Preserve accepted samples/index unchanged and create a separately versioned population/ledger under dataset ownership. Use2018–2024 and venue families SIGMOD, PVLDB/VLDB, ICDE, SoCC, Middleware, ICDCS, OSDI and SOSP. Plan at most56 initial DBLP discovery strata (eight families by seven years), verify actual venue/year/type, select at most400 seed publications and200 extra repeated-author/hard-negative neighboring publications. Search responses are discovery only; ingest actual DBLP record XML. Retrieve corresponding OpenAlex/Crossref work metadata plus bounded ambiguous neighbors and public ORCID records for actually observed IDs. Missing IDs remain represented; evidence strata are not labels.

| Proposed hard bound | Value |
| --- | ---: |
| Distinct ingestion records |2,060 total:600 DBLP,800 OpenAlex,600 Crossref,60 ORCID|
| All HTTP attempts, including retries/metadata |2,400 total; per-source750/850/650/100 respectively (all limits apply)|
| Total response bytes across attempts |256 MiB|
| Discovery response / ingestion record |2 MiB /1 MiB|
| Network concurrency / aggregate rate |1 / at most1 request per second, further limited by upstream headers|
| Request timeout / total wall clock |20 seconds /75 minutes, each bounded by remaining allowance|
| Retries |At most2 per request within all other budgets|
| Eligible candidate pool target |300 unique pairs,240 initial plus up to60 reserve candidates|

Future acquisition must reserve request/byte/time allowance before dispatch, stream bounded decoded responses, stop with partial status on exhausted bounds/auth/access/schema/identity failures, and retry only bounded transient failures with Retry-After/backoff. No paid fallback, full-corpus fallback, unlimited retries, silent cap increase or accepted-input overwrite. The cap is a first bounded attempt, not a guarantee of sufficient supply or an authorization to acquire now.

Retain original response hashes, sanitized request/status/allowed headers, retrieval time, source identity, selection/transform versions and output record locators/hashes. Flatten OpenAlex results[] to supported work JSONL; compose DBLP single-record XML preserving originals; preserve Crossref supported envelopes and public ORCID JSONL. Use explicit new snapshot/retrieval CLI arguments and a separate preparation config; the current aggregate maxLocalSampleRecords=100 must be raised deliberately within the bounded population. No demonstrated Hadoop production parser repair is required yet.

Freeze source/candidate population and leakage groups before labels or prediction-driven selection. Group actual shared endpoints/parent works, source copies, near duplicates, known identity anchors and conservative OpenAlex-author hypotheses; hypotheses used to prevent leakage are not identity truth. Same venue/common-name blocks alone do not make one identity group. Diagnose component sizes; proposed max6 selected pairs/component implies at least7 development and34 held-out components, preferably considerably more. If groups cannot support the split, expand disjoint neighborhoods within an explicitly reviewed bound, never split connected leakage groups just to reach counts.

User target remains40 development and200 held-out actual reviews. Suggested balanced per-type allocation (20+20 development,100+100 held-out) is flexible and not a course quota. Reserve pairs stay in their original split; retain every uncertain label and report any extra review/binary coverage shortfall. Candidate-conditional metrics do not measure global matching/blocking recall.

Current access/license references checked by dataset owner:

- DBLP search/record APIs: https://dblp.org/faq/How+to+use+the+dblp+search+API.html and https://blog.dblp.org/2020/08/18/new-dblp-url-scheme-and-api-changes/ . DBLP metadata license: https://dblp.org/faq/Under+what+license+is+the+data+from+dblp+released.html .
- OpenAlex current authentication/paging: https://help.openalex.org/api/authentication/ and free-allowance/discovery costs https://help.openalex.org/access/example-costs/ . Older repository API assumptions require rechecking; free key may be needed for cursor continuation. No key inspected/configured.
- Crossref public/polite access: https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/ . student@uic.edu in the old script is an unverified placeholder; use public access or an actual user-supplied contact later.
- ORCID public read tutorial https://info.orcid.org/documentation/api-tutorials/api-tutorial-read-data-on-a-record/ and anonymous-access/quota documentation https://info.orcid.org/ufaqs/what-are-the-api-limits/ . Optional registered-token access is a concrete later prerequisite only if necessary; no secret inspection.
- API terms/public visibility apply; ORCID Public Data File CC0 waiver is not blanket authority for linked API resources: https://info.orcid.org/public-data-file-use-policy/ . Crossref abstracts can have separate copyright; future review evidence should retain needed bibliographic metadata and omit abstracts/full text unless separately justified.

### Limitations and next authorized scope

No240 reviews, gold-set measurement, calibrated thresholds, live adjudication or Phase5 acceptance exists. Scope5B, only after user-run5A review and explicit advancement: deterministic work/researcher input bridging, pair derivation/normalization/features/conflicts/scoring, four outcome exports and offline fake/disabled adjudication/cache, with independent tests. Source acquisition/review UI/labels/evaluation readiness remain5C; provider selection/live evidence5D; frozen held-out evaluation5E. No background work may cross this checkpoint.

### Final frozen verification and checkpoint

The final exclusive sbt check exited0 at2026-10-15 10:36:27 America/Chicago,399seconds. All236tests passed;22freshJUnit reports match stdout totals. All140source-freeze hashes unchanged, no added/missing scoped files. The generated test marker renewed only after the passing suites. Full stdout, failed attempts, compact JUnit/source/marker evidence and the initial corrected evidence-parser failure are retained under evidence/5a/. The nested injected format-stage error in CheckFailurePathSpec is expected passing failure-path coverage, not a failed final gate.

ER owner also reported successful static JSON parsing/design checks for four examples, fixture pair/label binding, local README links, separate illustrative threshold/band inequalities and weight sums, zero live allowances, and40/200/300 arithmetic. These are design inspections, not an implemented runtime loader. A formatting-only change was observed between domain tool writes/reads before the scheduled formatting slot; no semantic change was observed, no other worker claimed core writes, and the final140file freeze held throughout the gate.

All specialist tasks have completed and no gate/acquisition/provider job continues. reviewer-prompt.txt is a prepared handoff only; review.md records that no independent verdict has been supplied. No human-gate.md or accepted-commit.md was authored.


## Subphase 5A — external B1 repair checkpoint (in progress)

STATUS: BLOCKED-ON — original external review returned REQUEST-CHANGES; B1repair and fresh verification/recheck pending. The earlier COMPLETE status describes the original handoff only, not the returned review gate.
OWNER: Same core/ER/test owners; coordinator retains evidence. Full user-supplied verdict: review.md. Repair start: b1-repair-start.json; original handoff: history/5a-initial-handoff/.
WORK ORDER: B1only typed canonical authority namespace validation; N1–N9not expanded into current-subphase implementation. User approved N6ownership: Phase6spark-engineer owns canonical grouping/representative selection under modules/spark/**, domain owns shared contract changes. No Phase6execution authorized.
FILES CREATED: Repair-start/history evidence; current repair manifest will list all affected paths.
FILES MODIFIED: B1owned core files/tests/docs, ERREADME, independent tests and coordinator phase evidence only.
COMMANDS RUN: Pre-repair140sourcehashes verified unchanged; executable targeted red/green and full gate results pending.
TEST RESULTS: Original236test passing gate remains historical pre-repair evidence, not the fresh B1gate.
VALIDATION RESULTS: Narrow authority policy agreed: canonical doi/arxiv works,orcid researchers,strict closednamespace/entity meaning. OpenAlex/DBLPnative bindings and other observations preserved separately. Unknownaliases/casing/noncanonical forms failclosed; no5Bnormalization/matching implementation.
ASSUMPTIONS: Complete supplied B1description controls repair; its truncated acceptance subsection is preserved verbatim, not completed by invention.
RISKS: Deferred observations retain their disclosed limitations; no accuracy/humanlabel/provider evidence exists.
MANUAL ACTION REQUIRED: User-selected external5Arecheck after repair/gate packet. N6decision received explicitly; no further ownership permission needed.
BLOCKED-ON OWNER: Domain/test owners,then external reviewer/user.
BLOCKED-ON EVIDENCE: Pre-fix reproduction,post-fix regression,new frozen fullgate,recheck verdict.
NEXT GATE: CompleteB1repair,returnfresh reviewerpromptandstop;5Bnotauthorized.


## Subphase 5A — B1 repaired, fresh verification complete, external recheck pending

STATUS: COMPLETE — B1technical repair and fresh gates complete; no independent recheck approval or5Aacceptance inferred.
OWNER: `/root/phase5a_domain` core; `/root/phase5a_er` module documentation/authority agreement; `/root/phase5a_test` independent tests/evidence collection; `/root` serialized command execution and reports.
WORK ORDER: Repair only external blockerB1 and record explicitly approved N6ownership. No5Bimplementation. Full returned review:review.md; repair-start:b1-repair-start.json; exact8pathsource delta:b1-repair-source-delta.json; originalhandoff:history/5a-initial-handoff/.
FILES CREATED: ResolutionAuthoritySpec.scala and coordinator repair/evidence artifacts. Full current tracked/untracked inventory and hashes:review-inventory.json.
FILES MODIFIED: ResolutionContracts.scala, ResolutionValidation.scala, core ResolutionContractFixtures.scala/ResolutionContractSpec.scala, coreREADME, ERREADME and IndependentResolutionContractSpec.scala. No other sourcepaths changed versus reviewedstate.
COMMANDS RUN: Coordinator pre-fix independent target exit1(7pass/3B1fail); post-fix coretarget exit0(13pass); independenttarget exit0(11pass); fresh sbtcheck exit0(244pass). Exactcommands/env/output and permission/interruption provenance:test-report.md and evidence/5a-b1/.
TEST RESULTS: Fresh fullgate244tests:core112,Hadoop64,independent64,buildVerification4;23freshJUnit reports;zero failures/errors/skips. Completed2026-10-15 11:31:58 America/Chicago in398seconds. No repeatedgateafterpass.
VALIDATION RESULTS: New141file freeze unchanged throughoutgate, no added/missing scopedfiles. Marker renewed only after passing suites. Closednamespace codec rejectscase/aliases/unknownnames; canonicalvalues and entitycompatibility checked before componentconflicts. Actual mixedcaseORCIDABCbypass reproducedbeforefix and regressionpassesafterfix. Six originalfixture roundtrips pass; canonicalgroupingJSON remains byteidentical undernewtypedcodec (SHA86f3d22ed906457570b453d36bf20d4d1e87ca5262e270d6454f3fe7d5bde070), preserving legitimatev1canonicaloutput while rejectinginvalidinputs.
ASSUMPTIONS: Hardauthority allows canonical doi/arxivbase forWork,orcid forResearcher. Ingestion must normalize source spellings explicitly before assertion construction; rejected rawspellings remain sourceevidence. Native DBLP/OAworkkeys and OAauthorhypotheses cannot assert hardnonmerge. SemanticScholar/repository authority requires futurevalidated namespace/canonicalizer policy; no newsource/5Balgorithms now.
RISKS: N1–N5,N7–N9remain deferred as explicitlynonblocking in returnedreview. They are not silently ignored or claimedfixed. N6resolvedbyuser and namedincore/ERdocs:Phase6spark-engineer owns grouping/representatives modules/spark/**;domainowns sharedtypes. No Phase6authority granted. Source/evidence validation remains structural and exportercompleteness bound is future5Bmanifestwork; no humanlabels/provideraccuracyclaims.
MANUAL ACTION REQUIRED: Userruns fresh reviewer-prompt.txt and returnsfullverdict. No reviewerlaunched/selectedbycoordinator. Explicituserauthorizationstillrequired before5B,evenafterAPPROVE.
BLOCKED-ON OWNER: User-selected independentexternalreviewer/user.
BLOCKED-ON EVIDENCE: Returned5Arecheckverdictpending; no remainingobservedtechnicalgatefailure.
NEXT GATE: External5Arecheck. Allworkers/buildsstopped; no backgroundjobs. No commits/push/acquisition/provider/AWS/laterphasework.


## Subphase5A — B2/N10 repair checkpoint (current, verification running)

STATUS: BLOCKED-ON — source/targetedverificationready; freshfullgateandexternalrecheckpending.B1isCLOSEDbyactualuser-suppliedindependentrecheck.
OWNER: core/domain, ERmoduledocs, independenttestowner, coordinatorserializedgate/evidence.
WORK ORDER: FixnewB2source-groundingblockerandN10knownprofilecoverage,clarifyN11supersededN6pendingtext; only5A. Fullverdictreview.md,detailsrepairs.md; b2-repair-start.json/history/5a-b1-recheck/preservepreviousreviewedstate.
FILES CREATED: coreResolutionGroundingSpec.scalaandevidence/5a-b2/;newsourcefreeze/delta.
FILES MODIFIED: Eightsource/doc/testpathslistedb2-repair-source-delta.jsonpluscoordinatorreports. No publicAPI/schema/StableIds/sourcefacts/builddependencieschanged.
COMMANDS RUN: Pre-fixindependent14tests exit1,11pass3newfail;post-fixcore20/20pass,independent17/17pass(aftertest-onlyoldfixturecorrection);freshsbtcheckrunningon142freeze.
TEST RESULTS: Targetedsuitespass;freshfullgatenotyetclaimed.Prior244gateashistoricalonly.
VALIDATION RESULTS: Assertionssource-boundandallrecognizedsupportedknownfactscoveredforactualsnapshottedendpoint. Falseabsentarxivpositivefixturescorrectedbyrealcarriedsyntheticfacts; canonicalgroupingwireunchangedgenuineDOIroundtrip. No reportedidentityaccuracy/gold/modelcalibration/providerresults.
ASSUMPTIONS: Grounding-onlynamespace/canonicalcomparisoniscarriedsourceconsistency;5Bextractor/scorerstillabsent. SourceIDs/rawfactsremainimmutable.
RISKS: N1–N5/N7–N9remainnonblocking;manifestbinding/exportcompletenessfuture.Noindependentrecheckapprovalinferred.
MANUAL ACTION REQUIRED: Afterfreshgate,userlaunchesexternalrecheckandreturnsfullverdict;5Brequiresseparateexplicitauthorization.
BLOCKED-ON OWNER: Coordinator/testevidence,thenuserexternalreviewer.
BLOCKED-ON EVIDENCE: Freshfullgate142hashes/JUnit/marker,andreturnedrecheck.
NEXT GATE: Finishobservedverification,returnfreshprompt,STOP.


## Subphase5A — B2/N10 repaired; N11 clarified; fresh verification complete

STATUS: COMPLETE for5Atechnicalrepairandverification; externalrecheckpending, no5AorPhase5acceptanceinferred.
OWNER: /root/phase5a_domaincore; /root/phase5a_ermoduledocs; /root/phase5a_testindependenttests/postgateinspection; /rootcoordinatorserializedexecution/evidence. Allworkers/buildsstopped.
WORK ORDER: User-suppliedrecheckclosedB1,requestedB2sourcegroundingandoptionallyN10profilecoverage; coordinatorincludedN10minimalallknownfactconsistencyandN11supersededN6pendingtext. No5Bimplementation.OtherN1–N5/N7–N9remainexplicitnonblockingfollowups.
FILES CREATED: coreResolutionGroundingSpec.scala; b2-repair-start.json,b2-repair-source-delta.json, history/5a-b1-recheck/ and evidence/5a-b2/. Currentcompletechanged/untrackedinventory+hashes:review-inventory.json.
FILES MODIFIED: Eightcurrentrepairsource/doc/testpathslistedb2-repair-source-delta.json:coreREADME,ResolutionValidation.scala,ResolutionValidationContext.scala,ResolutionAuthoritySpec.scala,ResolutionContractSpec.scala,newResolutionGroundingSpec.scala,ERREADME,IndependentResolutionContractSpec.scala. Coordinatorreportsupdated; nootherproductionchanges.
COMMANDS RUN: Beforefixindependent14tests:exit1,11pass3B2/N10fail;afterfixcore20/20pass;independent17/17passaftertest-onlyfixturecorrection. FreshJava17 sbt -batch check:exit0,399seconds06:39,completed2026-10-15 12:08:06 America/Chicago. Exactcommands/failedoutputs/results:test-report.mdandevidence/5a-b2/.
TEST RESULTS: Fresh257testspass:core119,Hadoop64,independent70,build4;24freshJUnitreportsmatchstdout;zerofailures/errors/skips. Original244/236gatespreservedashistory,notfreshrepairclaims.
VALIDATION RESULTS: All142frozenhashesunchanged,noadded/missingscopedfiles. Marker renewed1792084086514afterpassingtests. Assertionsrequirecanonicalclosednamespace/entitymeaningandactualexactobservationfacts. Allrecognizedsupportedfactsfromeachcoveredendpointmustbeasserted; omissioncannoteraseconflictingprofile/mention/workfacts. Realno-IDmembersremainvalidwithoutinventedassertions. ProfilesownORCID,mentionactualmemberobservedOrcid,workpreferred/declaredDOI/arxiv/Crossrefkeyandactivitypreferred/self-referencefactsboundincontext. Related-onlyORCIDreferencecannotbeupgradedtoownworkidentity. Canonicalsourcevariantsandversionedarxivsourcecanbindbaseassertionsunderexplicitgrounding-onlyrule; rawsourcefactsunchanged.
ASSUMPTIONS: Groundingiscarriedsourceconsistency,notclaimsourcefactualtruthornewmatchingpolicy. Knowncontradictoryfactsrequireallassertionsandcomponentconflictthenfails; unsupportedidentifiersremainobservations. Schema/publicAPI/StableIdsunchanged. OriginalgroupingJSONcontinuesgenuinesourceDOIfactroundtripbyte-identicalSHA86f3d22ed906457570b453d36bf20d4d1e87ca5262e270d6454f3fe7d5bde070.
RISKS: Exportercompletenessbeyondsuppliedcontextstillfuturemanifestbinding. N1performance,N2path/scoresemantics,N3existingenumconvention,N4nativekeyaliases,N5strictunknownfields,N7ineligiblepaircounts,N8rules/LLMreasonmapping,N9runbundlebindingremaindeferred. No labels/provider/matchingaccuracyclaims. N6approvedownershipunchanged; N11historicalpendingtextmarkedassuperseded.
MANUAL ACTION REQUIRED: Userrunspreparedfreshrecheckpromptandreturnsfullverdict. No reviewerlaunchedorselectedbycoordinator. Explicitadvancementstillneededbefore5B.
BLOCKED-ON OWNER: User-selectedexternalreviewer/user.
BLOCKED-ON EVIDENCE: ReturnedB2/N10recheckverdictpending; noobservedtechnicalgatefailure.
NEXT GATE: External5Arecheck. STOP; nofurtherimplementation/backgroundjobs/commit/push/acquisition/provider/cloud/laterphasework.


## Subphase 5B start — 2026-10-16

STATUS: IN PROGRESS (not a completion or acceptance claim).
OWNER: Coordinator with ER/domain/test native owners named in 5b-baseline.json.
WORK ORDER: Implement 5B only under the user statements in prompt.md.
FILES CREATED: 5b-baseline.json; immutable prior handoff copies in history/5a-final-handoff/.
FILES MODIFIED: Coordinator appendices in prompt.md and owner-report.md; owner implementation pending.
COMMANDS RUN: git status --short (empty), git branch --show-current (phase-5), git rev-parse HEAD (4ac236fcb01825b73635fa4c762a35bed4b362cd); read-only instruction/contract/plan/course inspection.
TEST RESULTS: No 5B tests run yet. Previous 257-test gate is historical 5A evidence.
VALIDATION RESULTS: All 142 prior frozen source hashes match committed start. Public API proposal agreed; minimal shared authority accessor approved.
ASSUMPTIONS: Existing real Phase 4 sample runs must be reverified by reader; no additional datasets assumed.
RISKS: Data population remains insufficient; thresholds uncalibrated; complete external B2 APPROVE text not supplied.
MANUAL ACTION REQUIRED: User launches external review after 5B handoff; no action needed during implementation.
BLOCKED-ON OWNER: None initially.
BLOCKED-ON EVIDENCE: Current implementation and fresh gate pending.
NEXT GATE: Frozen-source targeted/full verification, complete external reviewer prompt, STOP.


### 5B domain-owner handoff

STATUS: COMPLETE implementation and root-observed targeted verification.
OWNER: `/root/phase5b_domain`.
WORK ORDER: Public read-only `context.groundedAuthority(endpoint)` only.
FILES CREATED: Core ResolutionAuthorityConsumerSpec.
FILES MODIFIED: Core ResolutionValidationContext.scala and README.
COMMANDS RUN: Owner inspected instructions/contracts/diff and `git diff --check` (exit 0); root ran serialized targeted core command recorded in test-report.md (exit 0).
TEST RESULTS: 24/24 targeted tests pass including four external-package public-consumer tests.
VALIDATION RESULTS: Production logic unchanged; only method visibility/documentation changed, identical B2/N10 grounding semantics and v1 IDs/wires.
ASSUMPTIONS: ER uses actual evidence refs; the accessor establishes source consistency, not identity.
RISKS: N1 component-index API deferred because 5B does not group components.
MANUAL ACTION REQUIRED: None now.
BLOCKED-ON OWNER: None for core implementation.
BLOCKED-ON EVIDENCE: Eventual integrated full gate.
NEXT GATE: Owner core writes stopped; ER consumes public API; user-run independent review after full 5B gate.


### 5B execution interruption and resumption

The ER implementation agent returned a platform usage-limit error during repair of the first targeted failures. No completed repair or test pass was inferred. The user then explicitly asked, “can you keep going?”; coordinator resumed the same owner/task from saved files. Existing ownership, subphase limits and user-run review gate remain unchanged. No model override, extra service purchase, reviewer invocation or later-subphase work was performed.


## Subphase 5B owner/test handoff and real-data verification

STATUS: COMPLETE implementation and targeted/demo verification; frozen full gate pending.
OWNER: `/root/phase5b_er`, `/root/phase5b_test`, `/root/phase5b_domain`; coordinator collects evidence.
WORK ORDER: Deterministic work/researcher resolution and offline fake/disabled adjudication only.
FILES CREATED: ER10productionScala files,4runtime/prompt/schema resources,OfflineResolutionSpec; coreexternal-packageconsumer spec; tests12independentScala files (10suites+2helpers). Complete paths in finalinventory.
FILES MODIFIED: Corecontext/README; ERREADME; coordinator phase reports/evidence. No build/dependency/Hadoop/dataset/constitution edit.
COMMANDS RUN: Owners inspected instructions/contracts/source and owned diffs; no owner launched sbt. Root serialized all formatting/compilation/tests and CLI runs, with exact results/failed attempts in test-report.md and evidence/5b/.
TEST RESULTS: Core27targeted pass; latestER14pass; independent60priorfocusedpass plus affectedInput6pass including61stnewcase. Previous full-independent run128/130 exposedone strict-JSONdefect andoneoverstricttransportassertion, bothrepaired/targetedverified. Final simultaneous fullgatepending.
VALIDATION RESULTS: Real completedPhase4input nowproduces18traceablecomparisons withtypedfour-outcome files,9acceptedlinks,total3hardconflicts,completeconstraints andverifiedmanifestbindings. Two disabled runslogicalequivalent;fake-demo0eligiblecalls honestlyreported. All170frozenhashes currentlyunchanged.
ASSUMPTIONS: Existingtinyrealportfolioonly; no additionaldataset assumed. RuntimepolicyexplicitlyUNCALIBRATED.
RISKS: No240humanlabels/calibration/evaluation/accuracy/blockingrecall/liveprovider evidence; no grouping. Arbitraryinjected JVM adapter cannotbeforciblyterminated;ifitignoresinterrupt runnerfusesfuturecalls; providedfakebounded. Hashes establishinternalconsistency,notexternalauthenticity.
MANUAL ACTION REQUIRED: User launches externalreviewafterpacket; fullB2APPROVEreportwasnotprovided, humanstatusapprovaland5Bauthorizationrecordedwithoutinventingreviewerwords.
BLOCKED-ON OWNER: Coordinatorfullgate/evidence, thenuserexternalreview.
BLOCKED-ON EVIDENCE: Finalfullgateexit/JUnit/marker/freezeverification.
NEXT GATE: Complete5BpacketandSTOP;5Cnotauthorized.


## Subphase 5B final technical verification — 2026-10-16

STATUS: COMPLETE implementation and technical verification; external review pending.
OWNER: Coordinator, with `/root/phase5b_domain`, `/root/phase5b_er` and `/root/phase5b_test`.
WORK ORDER: User-authorized 5B only, based on committed 5A `4ac236fcb01825b73635fa4c762a35bed4b362cd`, branch `phase-5`, initially clean.
FILES CREATED: 28 new source/test/resource files: one core consumer test, 15 ER files, and 12 independent test/helper files. Coordinator baseline, source delta, reports, diffs, inventories, command logs and retained demonstrations are under this phase directory.
FILES MODIFIED: Three existing source/document paths: core validation context and README; ER README. No build, dependency, Hadoop, dataset or constitutional file changed. Complete paths and hashes are in review-inventory.json and 5b-source-delta.json.
COMMANDS RUN: Exact sbt argv, Java/logback environment, logs and exit codes are in evidence/5b/commands.json. Root serialized all builds. Final `sbt -batch check` exited 0, reported 399 seconds, completed 2026-10-16 14:52:47 America/Chicago. Root post-gate collector exited 0 with valid=true. `git diff --check` passed. A read-only `ps` inspection was sandbox denied; it was not a build/test failure and was not needed to establish the terminal build result.
TEST RESULTS: 339 passed: core 126, Hadoop 64, entityResolution 14, independent 131, build verification 4. Thirty-six fresh JUnit reports, zero failures/errors/skips. All 61 new independent 5B cases ran in that final gate. Earlier failures, fixes and targeted passes remain retained. The nested injected format-stage failure is expected passing CheckFailurePathSpec coverage.
VALIDATION RESULTS: All 170 frozen source hashes unchanged, with no added or missing scoped files. The generated success marker was renewed after all suites (mtime 1792180367522). Three actual-input CLI runs completed: two disabled and one fake, each 18 comparisons, zero fake/live calls. Disabled outputs are logically equivalent under the explicitly listed processing-field exclusions; source evidence and complete constraint bytes remain significant. All retained demo file hashes, sizes, inventories, completion and constraint bindings verified.
ASSUMPTIONS: Runtime settings are uncalibrated examples. Actual model calls were ineligible on this tiny real sample; injected synthetic tests establish offline adapter/cache mechanics. User approval and advancement statements are recorded without inventing an external B2 APPROVE report.
RISKS: No human labels, calibrated accuracy, blocking recall, live provider evidence or full Phase 5 acceptance. Population remains insufficient for 40 development plus 200 held-out real human reviews. N1 scaling and existing N3 wire convention remain disclosed; generic CoreJson remains broader, while ER boundaries parse strictly. Arbitrary JVM adapters cannot be forcibly killed if they ignore interruption; the runner fuses subsequent calls, and the provided fake is bounded. Hashes establish internal consistency, not external authenticity.
MANUAL ACTION REQUIRED: User runs the complete reviewer prompt and returns the full verdict. No commit or push was made.
BLOCKED-ON OWNER: User-selected external reviewer.
BLOCKED-ON EVIDENCE: Independent 5B verdict.
NEXT GATE: External 5B review and any routed repairs; explicit user authorization required before 5C. All specialist workers and builds are stopped. No background acquisition, live calls or later-subphase work exists.


## Subphase 5B external blocker repair — owner handoffs

STATUS: COMPLETE implementation and targeted verification; full gate pending.
OWNER: Same domain, ER and independent test owners; coordinator records this handoff.
WORK ORDER: Repair external B1/B2 and bounded related observations, staying within 5B.
FILES CREATED: ER PathIsolation.scala and ComparableEvidenceSpec.scala; independent IndependentResolutionRepairSpec.scala and IndependentResolutionPrepBridgeRepairSpec.scala.
FILES MODIFIED: Seventeen reviewed source/document/resource paths, listed in 5b-repair-source-delta.json. Four new files; no removals.
COMMANDS RUN: Owners inspected source/diffs and used owned edits; no owner launched sbt. Root ran pre-fix regressions, core formatting/tests, ER/independent formatting/tests and three v2 actual-input CLI runs. Exact commands and retained results are in test-report.md and evidence/5b-repair/.
TEST RESULTS: Five pre-fix failures reproduced; post-fix core30/30, module19/19 and independent70/70 passed. One intermediate owner-test compilation failure was fixed by qualifying the run constant, without changing behavior.
VALIDATION RESULTS: DOI suffix compatibility is source-grounded; incomparable feature representations are missing, not mismatches; versions/fingerprints changed. Physical paths are isolated, model reasons agree with outcomes, catalog authority matches core, and empty names remain unavailable. Actual real-data reruns preserve18comparisons and zero calls; two disabled outputs are logically equivalent.
ASSUMPTIONS: Existing DOI token semantics remain authoritative; no new external DOI interpretation is claimed. Runtime policy stays uncalibrated.
RISKS: N-1 remains partially mitigated but open; N-2/N-8/N-9 deferred. No identity accuracy, human review or live-provider evidence.
MANUAL ACTION REQUIRED: User launches external recheck after the final packet.
BLOCKED-ON OWNER: Coordinator verification, then user-selected reviewer.
BLOCKED-ON EVIDENCE: Fresh full gate and external recheck verdict.
NEXT GATE: Frozen full gate, new reviewer prompt, stop. All specialist writers stopped.


## Subphase 5B B1/B2 repairs — final technical verification

STATUS: COMPLETE repair implementation and verification; independent recheck pending.
OWNER: Coordinator with `/root/phase5b_domain`, `/root/phase5b_er` and `/root/phase5b_test`.
WORK ORDER: Repair the two external blockers within 5B; no 5C advancement.
FILES CREATED: Four source/test files and coordinator repair evidence. Complete paths and hashes are in 5b-repair-source-delta.json and review-inventory.json.
FILES MODIFIED: Seventeen reviewed source/document/resource paths; no removed source files. No Hadoop production, dataset, build/dependency, StableIds formula, source schema, constitutional or human-decision edits.
COMMANDS RUN: Exact sbt arguments, environment, logs and exits are in evidence/5b-repair/commands.json. Final `sbt -batch check` exited 0, reported 409 seconds, completed 2026-10-16 15:29:06 America/Chicago. Post-gate collector exited 0 valid=true; `git diff --check` passed. No source changes or builds after that gate.
TEST RESULTS: 356 passed: core 129, Hadoop 64, entityResolution 19, independent 140, build verification 4. Thirty-nine fresh JUnit reports; zero failures/errors/skips. All 70 new independent 5B cases ran simultaneously. The five originally failing regressions now pass. Expected injected nested format failure remains passing CheckFailurePathSpec coverage.
VALIDATION RESULTS: All 174 frozen hashes unchanged, no added/missing scoped files; generated success marker renewed after all tests (mtime 1792182546329). B1 actual Hadoop bridge accepts and exports percent/query/SICI literal DOI suffixes before successful ER resolution, while conflicting values remain conflicts. B2 real-input same-DOI cross-source venues are unavailable; independent available-feature score is 1.0 instead of reproduced 0.9. Feature/policy versions are v2. Three actual-input runs succeed with 18 comparisons and 0 fake / 0 live calls; disabled logical replay and complete output inventories/hashes verify. Old initial handoff and evidence remain retained unchanged.
ASSUMPTIONS: Existing DOI token semantics are preserved; runtime weights remain uncalibrated. Synthetic regressions are not acquired datasets or human labels.
RISKS: External N-1 remains open despite default bibliographic shortcut being disabled: generic titles can still score-accept. N-2 scaling/indexing, N-8 dropped-pair quota and N-9 staging/rename follow-ups remain deferred nonblocking. N-7 same-publication researcher cases and OpenAlex-carried ORCID attribution require explicit future sampling/evaluation strata. No accuracy, blocking recall, calibration, live-model, human-review or final Phase 5 acceptance is claimed.
MANUAL ACTION REQUIRED: User launches the saved/displayed external recheck prompt and returns the complete verdict. No reviewer was invoked by manager or workers. No commit/push, acquisition, live call or 5C work occurred.
BLOCKED-ON OWNER: User-selected independent reviewer.
BLOCKED-ON EVIDENCE: External repair recheck APPROVE or REQUEST-CHANGES.
NEXT GATE: External 5B recheck and any routed repairs; explicit user authorization required before 5C. All workers and builds have stopped.

## Subphase 5B — review and human approval received

The user returned the independent APPROVE closing B1/B2, then explicitly stated: "alright I approve the change, now give me a one line commit message for this change". This supersedes the preceding pending-review status. The complete external verdict is retained in evidence/5b-repair/external-recheck-approval.txt; review.md records the separate human approval and its provenance.

5B is complete with external review and explicit human approval. Remaining nonblocking findings stay documented and unfixed at the user's direction. This receipt changes documentation only; no new tests, implementation, commit or push were performed. Human-owned decision files remain unchanged. 5C and broader Phase 5 acceptance remain pending their respective explicit human decisions.


## Subphase 5C — implementation and readiness verification

STATUS: COMPLETE implementation and targeted/browser verification; frozen full gate is running. This status is superseded only by the observed final-gate addendum below.
OWNER: Coordinator with native owners `/root/phase5c_dataset`, `/root/phase5c_er`, `/root/phase5c_test`.
WORK ORDER: User authorized "alright let move to phase 5c" and later "so keep going". Scope is original plan §§10–14 5C only. Existing 5B nonblocking issues remain documented and unfixed at the user's direction.
FILES CREATED: `5c-source-delta.json` records every added implementation/data/test path; `5c-baseline.json` binds clean starting HEAD `c8342d25ba04dede26af10bedc5a76691824d1ca`. New ER queue/split, label importer, evaluator and CLI, offline review page/guide/sampling configuration; six independent Scala sources and two browser artifacts; four dataset scripts, dataset docs and three retained bounded populations. Coordinator evidence lives in `evidence/5c/`.
FILES MODIFIED: Existing ER CLI routing and module README; dataset script README. No core, Hadoop, build/dependency, source schema, original samples, constitutional or human-decision file changed. Previous 5B packet retained byte-for-byte from starting HEAD in `history/5b-final-handoff/`.
COMMANDS RUN: Exact coordinator argument arrays, environments, logs, timestamps and exits are in `evidence/5c/commands.json`. Retained acquisition commands/logs and immutable per-request ledger are linked by `datasets/entity-resolution/acquisition-session.v1.json`. First sbt sandbox attempt failed on the existing external cache lock; native-authorized retry succeeded. No simultaneous sbt builds ran.
TEST RESULTS: Targeted ER 25 and independent 21 tests passed. The independent suites cover prediction-blind deterministic grouped allocation, strict revisions/hash/entity/queue bindings, hand-computed confusion/four-outcome/coverage metrics, missing and invalid predictions, null denominators, held-out tuning refusal, cache provenance and feasible entity coverage. Eighteen Python tests passed; existing dataset manifest validation passed using an existing pinned verification environment, without installation. Actual browser receipt is `tests/browser/phase5c-review-observed.json`. Full-gate result is pending the addendum.
VALIDATION RESULTS: Final CS population contains 446 OpenAlex works, 10 Crossref works and 8 ORCID records, 464 source records total; no new DBLP data acquired. Final source validator checked 132 file hashes and original response membership. All 446 OpenAlex years are 2018–2024. The actual nine-job Hadoop run is `target/phase5c-prep-runs/bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3`; counters include 66 rejected rows and zero schema failures. Input/intermediate counter sums are not distinct source counts. The final real queue has 11,412 candidate pairs and 568 leakage groups; selected tasks use 100 groups with no shared group across partitions. Initial development is 20 Work + 20 Researcher; held out is 100 Work + 100 Researcher, plus 10/50 reserves. 777 cross-partition candidate edges were explicitly excluded. Queue and split files are byte-identical across two generation runs. `real-readiness-summary.json` binds hashes and counts.
ASSUMPTIONS: Source metadata and identity hypotheses are evidence, never human labels. Source/code hashes are declared freeze metadata checked by coordinator; they do not establish authenticity or reviewer identity. Convenience selection and evidence-stratum oversampling support candidate-conditional reporting only.
RISKS: DBLP search returned a challenge, Crossref returned 429, and an ORCID response hit the configured cap; those sources were disabled without bypass. Initial author-neighborhood results included unrelated medical publications; the final offline CS filter excludes 154 OpenAlex works and 7 ORCID profiles, preserving both earlier populations and exclusions. Strong connected groups, unobserved identities and unrecognized near duplicates remain limitations. Existing 5B nonblocking defects remain unfixed. No accuracy, calibration, global recall, blocking recall or real-provider behavior is established.
MANUAL ACTION REQUIRED: User runs the independent 5C reviewer from the generated prompt and returns its full verdict. Actual human labels remain zero; do not begin labeling/provider integration/final held-out evaluation in this implementation checkpoint. Future labeling must preserve original exports outside `target/` with backup.
BLOCKED-ON OWNER: Coordinator full-gate evidence, then user-selected reviewer.
BLOCKED-ON EVIDENCE: Observed full check and independent 5C verdict.
NEXT GATE: Final 5C packet and user-run review; explicit advancement before 5D. No reviewer, commit, push, cloud action or real model call was launched.

### Browser execution disclosure

The independent tester used native Microsoft Edge on the actual production review page with six synthetic tasks. Loading, safe literal source rendering, reviewer-ID requirement, Same/Different/Uncertain, navigation, undo, revision 3, export, wrong-queue rejection, refresh and saved-checkpoint resume were observed. Exported tool bytes match the tested resources. Automated annotations are test-only, clearly prefixed `synthetic-` in retained evidence, and count as zero human reviews.

An initial global new-tab/type-text shortcut mistakenly submitted the nonsecret local HTML path into an already-open ChatGPT study conversation. No queue, labels, file contents or credentials were sent. The tester disclosed this when discovered and subsequently selected observed tabs/controls, reacquiring state after concurrent user changes and a capture error. The coordinator informed the user. The browser receipt preserves this limitation; no screenshot/DOM instrumentation is claimed. All browser actions and source writers have stopped.


## Subphase 5C — final frozen verification and review handoff

STATUS: COMPLETE implementation and technical verification; external independent review pending. This supersedes the earlier running-gate status.
OWNER: Coordinator; all three specialist owners have completed and stopped.
WORK ORDER: Authorized 5C only; no 5D or final Phase 5 acceptance.
FILES CREATED / FILES MODIFIED: Complete tracked/untracked inventory and hashes in review-inventory.json; implementation/data/test delta in 5c-source-delta.json.
COMMANDS RUN: Exact commands, environments, timestamps and exits in evidence/5c/commands.json. The final `sbt -batch check` exited 0. No source changes occurred during or after that gate.
TEST RESULTS: 383 tests passed: {'core': 129, 'hadoop': 64, 'entityResolution': 25, 'independent': 161, 'buildVerification': 4}. 44 fresh JUnit reports, zero failures/errors/skips. Source freeze verifies all 509 files unchanged, no added/missing scoped files. Generated success marker renewed after all suites. Expected nested injected failure remains passing CheckFailurePathSpec coverage, not a failed full gate. Eighteen Python tests and both dataset validators also passed.
VALIDATION RESULTS: Real 40-development/200-held-out queue plus 60 reserves; entity allocations 20/20 and 100/100; byte-identical queue/split replay; disjoint selected evidence groups; all exported tool bytes match browser-tested resources. Actual browser save/refresh/resume and strict synthetic checkpoint CLI import/evaluator smoke checks passed. All 28 retained final Hadoop export part hashes remain unchanged. Historical 5B packet matches its committed versions. All 509 source hashes match final gate.
ASSUMPTIONS: Tests establish behavior only; source metadata and synthetic annotations are not human labels.
RISKS: Public-source access limits, convenience sampling, unknown-identity leakage, unmeasured blocking recall, browser automation incident and user-deferred 5B nonblocking findings remain disclosed.
MANUAL ACTION REQUIRED: User launches the saved/displayed read-only 5C reviewer prompt and returns full verdict. Human reviews remain 0/240; labels, provider choice/budget/live calls and final held-out evaluation remain later gates.
BLOCKED-ON OWNER: User-selected independent reviewer.
BLOCKED-ON EVIDENCE: Independent 5C verdict; no technical implementation gate remains unverified.
NEXT GATE: External 5C review, any required repairs, and explicit user advancement authorization before 5D. No reviewer was triggered. No commit/push occurred. All workers/builds/acquisition/browser actions have stopped.

Final gate timing: sbt reported 412 seconds, completed 2026-10-16 16:31:44 America/Chicago. Code/source freeze remained unchanged. `prepare-evaluation-predictions` has adapter binding/cache adversarial tests; it was not executed end-to-end on the expanded real population in 5C. No real prediction-versus-gold evaluation was run.

Final whitespace check: implementation source, datasets, tests and phase Markdown reports pass `git diff --check` when checked directly. The broad check flags line 20 of the generated whole-Phase-5 `implementation.diff`: a literal blank patch-context line contains one space. This is retained patch syntax from the faithful generated diff, not whitespace in changed implementation source; the patch is not altered to hide it. Final path/hash inventory was rechecked after documentation finalization.


## Subphase 5C B1/B2 repair verification

STATUS: COMPLETE blocker implementation and targeted verification; fresh frozen full gate pending.
OWNER: Coordinator with native ER, dataset and independent test owners; all specialist writes stopped.
WORK ORDER: User instruction "fix the blockings bugs first for me" after independent REQUEST-CHANGES. Full report preserved in review.md and evidence/5c-repair/external-review.txt. No nonblocking fixes or later-subphase work authorized.
FILES CREATED: Durable exact prepared population (68 files), sibling retention manifest, retention script/tests/README, three independent Scala repair/probe files, coordinator evidence. Exact repair scope is 5c-repair-source-delta.json (75 added, 11 modified, 0 removed).
FILES MODIFIED: ER queue/evaluation/CLI and binding-only page/guide/README/test adaptations; existing dataset docs and independent evaluation tests. Core/Hadoop/build/StableIds/formulas/originalsamples/constitutional/human-decision files remain untouched.
COMMANDS RUN: Exact args/environment/exits in evidence/5c-repair/commands.json; all sbt builds serialized. B1 red tests ran before ER production changes; actual durable replay ran through the compiled Scala loader/candidate builder, not just Python hashing.
TEST RESULTS: Before repair, two B1 tests failed as intended against unchanged reviewed production. After repair, 25 owner tests passed; first independent run: 27/28 passed with one invalid new synthetic snapshot fixture, then the corrected run: 28/28 passed. Negative retention tests now prove valid initial loading and real byte mutations. New cases demonstrate P0 checkpoints and queue identity surviving real offline P1 policy/model/adjudication config/code transitions, while changed source/candidate/task evidence remains rejected/invalid. Dataset owner reports eight new retention tests and 26 total Python tests passed; coordinator retains fresh verification separately.
VALIDATION RESULTS: Exact durable input reproduces original inputEvidenceHash 57efd81957e5eec9194d4b5c42f6ef170213640f148b56bf8b99a51d1d09d1fe and candidatePopulationHash 9381588e35a418a84a22e9a680db4ab7886a8d33cf9463166edc1222cd8a5581, 11,412 pairs; typed 456 works / 8 profiles / 465 activities identical. Required input is datasets/entity-resolution/prepared/bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3, 49,547,452 bytes / 68 files, none ignored by Git. A regenerated queue from this durable root succeeds with 240 initial + 60 reserve tasks; final replay/allocation proof follows. New sourcefreeze binds 584 files.
ASSUMPTIONS: Mutable model/policy/code metadata describes prediction runs and does not redefine human annotation identity. Dataset retention follows existing datasets/** ownership, not a constitutional change or invented human ratification. Hashes prove consistency, not authenticity.
RISKS: Required exact retention adds 47.3 MiB. Nonblocking N1–N8, including size and old acquisition-script/command-ledger limitations, remain documented/unfixed. Original browser evidence is historical; no browser actions or real-queue load were added in this blocker-only round. No real labels, calibration or live evidence exist.
MANUAL ACTION REQUIRED: Wait for fresh full gate and user-selected external recheck before labeling or advancement. Preserve durable inputs and future original annotations.
BLOCKED-ON OWNER: Coordinator full gate; then user-selected external reviewer.
BLOCKED-ON EVIDENCE: Final queue replay/hash/allocation, frozen full gate and returned external verdict.
NEXT GATE: Complete current 5C repair packet, display recheck prompt and stop. No reviewer launch, acquisition, 5D/provider work, commit/push or human labeling occurred.


## Subphase 5C B1/B2 — final technical repair gate

STATUS: COMPLETE blocker repairs and fresh technical verification; independent external recheck pending. This supersedes the preceding pending-gate status.
OWNER: Coordinator; ER, dataset and independent test owners have completed and stopped.
WORK ORDER: Repair only external 5C B1/B2 under the user's explicit instruction.
FILES CREATED / FILES MODIFIED: 5c-repair-source-delta.json binds 75 additions, 11 modifications and no removals against the exact reviewed 509-file freeze. The new freeze binds 584 files. Complete tracked/untracked inventory is review-inventory.json; old packet remains in history/5c-initial-review/.
COMMANDS RUN: Exact commands, environment, timestamps and exits are retained in evidence/5c-repair/commands.json; independent dataset checks in dataset-checks.json. Final `sbt -batch check` exited 0. All builds serialized; no source edits during final gate.
TEST RESULTS: 390 tests passed: core 129, Hadoop 64, ER 25, independent 168, build verification 4; 46 fresh JUnit reports; zero failures/errors/skips. All 584 source hashes and scoped path membership remain unchanged; generated success marker renewed after all suites. Expected nested injected failure is passing CheckFailurePathSpec coverage. Two original B1 failures are now green; post-fix target 25 ER +28 independent passed after one disclosed synthetic-fixture correction. All 26 Python tests and 68-file durable validator passed.
VALIDATION RESULTS: B1 queue identity excludes mutable matcher settings; unchanged P0 annotations survive later P1 policy/model/adjudication config/code, and evaluation records actual P1 run provenance. Changed input/candidates/task evidence remains rejected/invalid. Rebuilt real queue reads the durable input; all 300 tasks and task evidence plus split are unchanged from initial 5C, while queuehash appropriately changed before any real labeling. Two runs produce byte-identical queue/split/generation audit. Allocation 40 development (20 Work /20 Researcher), 200 held-out (100 Work /100 Researcher), 60 reserves; 568 groups /100 selected; 777 cross-partition skips. B2 retains 68 byte-identical files /49,547,452 bytes outside target and reproduces original input 57efd819... and candidates 9381588e... over 11,412 pairs; actual full hashes in durable-input-proof.json. No UUID normalization or original-payload rewrite occurred.
ASSUMPTIONS: Population/evidence/split define annotation identity; prediction-run metadata defines actual execution provenance. Dataset retention follows existing datasets/** ownership; no constitutional amendment or separate human ratification is inferred.
RISKS: All eight new nonblocking findings and prior deferred observations remain unchanged. Required exact input retention adds 47.3 MiB. Initial manual browser test evidence is historical; no browser actions or new real-queue load were performed in this blocker-only round. No accuracy, real labels, calibration or live-model result is claimed.
MANUAL ACTION REQUIRED: User launches external repair recheck and returns full verdict; no reviewer has been triggered. Do not label until recheck/human gate. Include durable input and manifest in any later approved commit.
BLOCKED-ON OWNER: User-selected independent reviewer.
BLOCKED-ON EVIDENCE: External 5C repair verdict.
NEXT GATE: External recheck, any necessary repairs, then explicit human advancement before 5D. No acquisition, provider/live calls, actual labels, commit/push or later-subphase work occurred. All workers and builds have stopped.

Final repair gate timing: sbt reported 411 seconds, completed 2026-10-16 17:05:28 America/Chicago. Direct source/dataset/test/phase-Markdown whitespace checks pass; the previously disclosed literal blank context line in generated whole-phase implementation.diff is retained as faithful patch syntax. No new source changes or tests after the gate.


## Approved 5C — bounded pre-commit cleanup

STATUS: Cleanup and real-queue load-only check complete; single requested full gate running.
OWNER: Coordinator; build-engineer owns newly assigned `.gitattributes`, test-engineer owns browser receipt, ER owner verifies optional guide line.
WORK ORDER: User supplied external APPROVE closing B1/B2 and explicitly requested evidence compaction, prepared-input byte attributes/validator, load-only real queue, optional provider-hypothesis warning, then one sbt check and stop. No source/logic changes authorized or made.
FILES CREATED: Four compact `.diff.manifest.json` replacements, exact regeneration/compaction evidence and 12 small historical compressed source versions; two test-owned real-load browser receipts; `.gitattributes` was already present and is preserved. Complete current inventory follows final gate.
FILES MODIFIED: Four giant patches removed by explicit instruction only after exact replay verification; their original hashes, byte counts and path/source inventories are retained in sibling manifests. Phase evidence reports/freeze/inventory updated. The one-line OpenAlex warning already existed at task start; preserved byte-for-byte. No application logic changed.
COMMANDS RUN: `compact-diffs.py.txt` reconstructed each original patch exactly before replacing it. `regenerate-diff.py.txt` independently recreated all four patches from Git and hash-verified source versions with original SHA-256/byte counts. Native tester loaded the exact repaired queue/page and made zero label/reviewer/checkpoint actions. Build owner checked all68 prepared-file `text` attributes unset; retention validator passed for68files/49,547,452bytes. Exact final sbt command/environment/status in evidence/5c-precommit/commands.json.
TEST RESULTS: Actual page displayed "0 of 240 initial tasks answered; 240 remaining", Work task1of240, blank reviewer and No answer selected. No annotations exist. Browser details are tests/browser/phase5c-repaired-real-load-observed.json. Single fresh sbt check pending its final addendum.
VALIDATION RESULTS: Four removed diffs total295,287,818bytes; replacement manifests930,048bytes plus51,672compressed historical bytes. Regeneration preserves exact historical patches. Required prepared data, v3 population and repaired queue/split/generation binding preserved; hashes in preserved-artifacts.json. Frozen scoped state now587files, including attributes and two load-only browser artifacts. Commit-candidate files currentlyabout125MB, largest22.3MB; final measurement follows final ledger.
ASSUMPTIONS: Size is logical working-tree bytes that would be candidates for committing, excluding ignored target/cache and Git object history; no commit staged or created. User supplied only the short external approval verdict, recorded exactly without invented reviewer commands.
RISKS: Earlier nonblocking findings remain except explicitly requested warning/load check. v1/v2 and old pre-repair queue/split remain untouched. optional-size-proposal.json recommends future archival with manifests and preserved provenance dependencies only after separate approval. Historical giant-diff hashes remain valid via exact regeneration; old reports/inventories remain historical.
MANUAL ACTION REQUIRED: User handles future commit; any optional additional archival requires separate approval. No commit/push performed.
BLOCKED-ON OWNER / BLOCKED-ON EVIDENCE: Coordinator's one full gate and final inventory measurement.
NEXT GATE: Final one-line commit message, then stop. No reviewer launched, human labels made or 5D started.


## Approved 5C pre-commit cleanup — final gate

STATUS: COMPLETE. External 5C B1/B2 APPROVE is recorded as user-supplied; bounded cleanup complete.
OWNER: Coordinator with build, ER and independent test owners. All worker actions stopped.
WORK ORDER: Exact user cleanup instruction in evidence/5c-precommit/user-work-order.txt; no 5D advancement, source logic change, commit or push.
FILES CREATED / FILES MODIFIED: Four authorized giant patches replaced with compact sibling manifests; original hashes/byte counts and exact Git regeneration verified for all four. Required prepared data, v3 population and repaired queue/split/generation-binding remain unchanged. `.gitattributes` already contained the user-assigned build-owner rule; all 68 prepared files verified text unset. The optional OpenAlex hypothesis guide line already existed; preserved once and copied exactly to exported guide. Two test-owned load-only browser artifacts added. No application logic or source data changed.
COMMANDS RUN: One and only one `sbt -batch check` after the cleanup freeze, exit 0. Exact args/environment/timing in evidence/5c-precommit/commands.json. Four standalone exact historical patch regeneration checks passed; retention validator passed. Direct source/data/test/phase-Markdown whitespace checks passed.
TEST RESULTS: 390 tests passed; {'core': 129, 'hadoop': 64, 'entityResolution': 25, 'independent': 168, 'buildVerification': 4}; 46 fresh JUnit reports, zero failures/errors/skips. All 587 frozen files unchanged, no scoped additions/missing files; generated success marker renewed after suites. Expected nested injected check failure is passing CheckFailurePathSpec coverage. Real repaired page loaded real repaired queue and displayed 0 of 240 initial tasks answered, with zero label clicks, annotations, reviewer entries or checkpoints.
VALIDATION RESULTS: Original four diff bytes total 295,287,818 replaced by 930,048 manifest bytes and 51,672 compressed historical source bytes, plus small helper/proof files. Exact original patch hashes reproduced after deletion. Largest commit-candidate file 22,313,459 bytes, below 50,000,000. Final exact file totals and no-file-over-50-MB confirmation in evidence/5c-precommit/final-size.json; current path/hash inventory in review-inventory.json. This logical size excludes ignored target/cache and Git history.
ASSUMPTIONS: No longer independent recheck report was provided beyond the exact supplied APPROVE (B1/B2 closed) text; no reviewer commands/findings invented. Historical report references to original giant patch hashes are preserved via manifests, not silently rewritten.
RISKS: v1/v2 raw copies and old pre-repair queue/split remain untouched. Optional archival is only proposed, with parent/provenance references preserved; separate user approval required before any such removal or validator adaptation. No human review, model accuracy or live-provider evidence is claimed.
MANUAL ACTION REQUIRED: User may commit the approved change; proposed message: Complete Phase 5C review tooling and preserve reproducible evaluation inputs.
BLOCKED-ON OWNER / BLOCKED-ON EVIDENCE: None for this bounded cleanup.
NEXT GATE: Stop; 5D remains unauthorized. No reviewer triggered and no commit/push performed.


## Approved 5C lean archival packaging — work performed

STATUS: Archival and non-sbt checks complete; single requested full gate running. Final result follows in a separate addendum.
OWNER: Dataset-engineer owns dataset archival/manifests/README commands; build-engineer owns .gitattributes; ER owner owns README pointer audit; coordinator owns old queue/split archival and phase evidence.
WORK ORDER: User explicitly authorized lean pre-commit packaging only: copy and verify before removing inactive v1/v2 payloads and old queue/split; preserve original parent manifests, v3, prepared input and current repaired queue. No application logic, data content, labels, commit/push or 5D change.
FILES CREATED / FILES MODIFIED: Two dataset archive manifests, two old queue/split archive manifests, compact verification and command receipts, current human-handoff pointer, source freeze and current inventory. Removed 177 inactive dataset payload files (31,229,073 bytes) and two old evidence files (11,015,758 bytes), only after every external copy was byte/SHA-256 verified. The original population manifests remain verbatim. Owner README commands now distinguish manifest-only history from complete populations; historical reports and human decisions are preserved. Attributes cover all datasets/entity-resolution/** and evidence/**/review-artifacts/** as requested.
COMMANDS RUN: Read-only dependency audit before deletion; archive copy and full per-file SHA-256 checks; external historical-population validation; current v3 validator; prepared-input retention validator; all Python dataset tests; git check-attr on all 215 applicable current files. Exactly one sbt -batch check started for this approved lean packaging task; evidence/5c-lean/commands.json records exact args, environment and outcome.
TEST RESULTS: Both validators pass; all 26 Python tests pass. Full sbt result pending final addendum. No test/source logic changed.
VALIDATION RESULTS: All 181 archived original files verified (179 dataset files plus queue/split), 42,271,794 bytes including retained parent manifests. Archive roots: /Users/danny/Documents/ScholarChain-archive/phase5c/dataset-history-20261017T005030Z and /Users/danny/Documents/ScholarChain-archive/phase5c/old-review-21978642c7. No active validator, test, evaluator CLI or current handoff requires removed payload paths. Current v3 and prepared input remain complete. All four previously compacted historical diffs regenerate exactly from external archive bytes and pinned historical README blobs; manifests now document this dependency. All 165 application/dataset-script/test source files match the prior freeze. New scoped freeze binds 412 current files. All 215 applicable text attributes are unset.
ASSUMPTIONS: External archives are durable local historical storage; another machine needs transferred archives for exact historical reconstruction. Current runtime inputs and repaired queue remain in the repository.
RISKS: External archives require separate preservation and backup. Old reports/inventories describe historical packets, whose removals are explained by appended notes and sibling manifests. No identity accuracy, labels or provider behavior is established.
MANUAL ACTION REQUIRED: Preserve the external archives; user handles any future commit. Final size, fresh gate and one-line commit message follow after completion.
BLOCKED-ON OWNER / BLOCKED-ON EVIDENCE: Coordinator's single integrated sbt gate and final freeze/inventory/size verification.
NEXT GATE: Finish packaging report and stop. No reviewer launch, labeling, commit, push or 5D.


## Approved 5C lean archival packaging — final gate

STATUS: COMPLETE. This supersedes the running-gate lean note above. User-supplied external 5C B1/B2 APPROVE remains unchanged; no additional review or later phase is inferred.
OWNER: Coordinator with dataset, build and ER owners; all writers and builds stopped.
WORK ORDER: User-approved archival packaging only. No application logic, source-data content, labels, commit, push, provider calls or 5D change.
FILES CREATED / FILES MODIFIED: Compact archive manifests and owner README/attribute updates; original historical population manifests preserved. Removed exactly 177 inactive dataset payload files and two old queue/split files after verifying their complete external copies. Current v3, durable prepared input, repaired queue/split/generation binding remain unchanged. Append-only reports, source-freeze.json and review-inventory.json bind current packaging. Historical packet reconstruction remains exact through the documented archive sources.
COMMANDS RUN: Both current validators and all Python dataset tests passed after removals. Exactly one sbt -batch check for this lean task exited 0, wall duration 413.402 seconds; exact environment/args/timing in evidence/5c-lean/commands.json. git diff --check for changed packaging paths passed. Final archive and frozen-content verification passed.
TEST RESULTS: 390 tests passed; module counts {"buildVerification": 4, "core": 129, "entityResolution": 25, "hadoop": 64, "independent": 168}. 46 fresh JUnit reports; 0 failures, 0 errors, 0 skipped. All 412 frozen scoped files unchanged, with no missing or added scoped files; generated success marker renewed after suites. All 26 Python dataset tests pass. Expected nested injected failure is passing CheckFailurePathSpec coverage.
VALIDATION RESULTS: All 181 archived original files rechecked SHA-256 and byte counts, including both original parent manifests. Dataset archive root: /Users/danny/Documents/ScholarChain-archive/phase5c/dataset-history-20261017T005030Z. Old evidence archive root: /Users/danny/Documents/ScholarChain-archive/phase5c/old-review-21978642c7. All 215 current applicable files have text unset. 165 application/dataset-script/test source files are byte-identical to the pre-lean freeze. Complete inventories, exact final logical byte totals and largest-file/no-file-over-50-MB check are in evidence/5c-lean/final-size.json and review-inventory.json; ignored targets/caches and Git history are excluded from commit-candidate size.
ASSUMPTIONS: External archives need separate preservation/transfer for exact historical reconstruction; current runtime inputs remain fully in-repository.
RISKS: This packaging pass does not establish human labels, accuracy or live-provider behavior. Previously deferred nonblocking observations remain deferred.
MANUAL ACTION REQUIRED: Preserve the external archive and manually commit if desired. Proposed one-line commit message: Complete Phase 5C review tooling with durable inputs and lean audit archives.
BLOCKED-ON OWNER / BLOCKED-ON EVIDENCE: None for authorized packaging.
NEXT GATE: Stop. No code reviewer triggered, commit/push performed or 5D started.


## Subphase 5D — authorized start and readiness

STATUS: IN PROGRESS; provider implementation/offline verification underway, live numerical budget and genuine human checkpoints pending.
OWNER: Coordinator; entity-resolution engineer implements only modules/entity-resolution/**; independent tester owns tests/**; dataset owner completed read-only review-input verification.
WORK ORDER: User authorized 5D and selected OpenAI GPT-6 Luna; exact user words and clean baseline recorded in prompt.md and evidence/5d/baseline.json. No live-call or numerical budget authorization inferred. No 5E, commit/push or reviewer launch authorized.
FILES CREATED / FILES MODIFIED: Provider-independent readiness receipts under evidence/5d/. Production/test inventory will follow completed implementation. Existing 5C artifacts remain immutable inputs.
COMMANDS RUN: Read-only Git/contract/plan/owner audit; official OpenAI model/pricing/structured-output documentation and authoritative course Phase5/6 fetched. Existing compiled API inspected development tasks only via ER-owned scratch probe, zero provider calls. Full exact commands and verification outcomes will be retained before handoff.
TEST RESULTS: No new test execution claimed at this checkpoint. Prior 5C gates remain historical. Independent tester has defined 5D transport, budget, schema, cache and development-only admission matrix.
VALIDATION RESULTS: Clean phase-5 starting HEAD61d32a38eaad5b2fc352acf0b7f85f3815c2336d. API IDgpt-6-luna verified in official docs; no dated snapshot invented. Blind page, guide, repaired queue/split/generation audit and prepared retention manifest hashes verified. All68prepared files/49,547,452bytes unchanged. No genuine human labels found in designated phase evidence;240initial reviews pending,60reserves separate. Selected50development tasks currently yield no naturally eligible LLM calls; full development-group demo eligibility is being checked separately without scoring held-out tasks.
ASSUMPTIONS: User model selection concerns project adjudication, not implementation-agent model routing. Actual usage/account access cannot be inferred from docs or a subscription.
RISKS: Live evidence may require additional development evidence if the existing admitted population has no eligible pair. No score/band manipulation or synthetic evidence substitution is allowed.
MANUAL ACTION REQUIRED: User labels the approved blind queue and supplies original checkpoints; later approves explicit numerical live budget and configures a runtime credential without sharing the key in chat.
BLOCKED-ON OWNER / BLOCKED-ON EVIDENCE: Numerical live approval, runtime credentials, actual human checkpoints, and naturally eligible development/demo evidence remain prerequisite gates; unaffected implementation continues.
NEXT GATE: Passing offline adapter tests and concrete request/budget approval, then only explicitly authorized bounded development calls; eventual user-launched external5D review.


## 5D implementation checkpoint — targeted verification

STATUS: Implementation ready for remaining coordinator gates; 5D acceptance not claimed.
OWNER: Entity-resolution engineer for modules/entity-resolution/**; independent test-engineer for tests/**; dataset-engineer for datasets/**; coordinator for phase evidence and serialized commands.
WORK ORDER: User-authorized OpenAI gpt-6-luna adapter and separately approved bounded development/demo pilot.
FILES CREATED: Five ER production files (LiveProvider.scala, OpenAIResponses.scala, LiveAdjudication.scala, LiveDemo.scala, LiveDemoCommands.scala), three adjudication resources, LiveDemoExportSpec.scala, seven independent fixture/spec files, bounded supplement acquisition/tests and manifests, and coordinator receipts under evidence/5d/.
FILES MODIFIED: ER CLI routing, existing leakage-anchor accessor visibility, ER README and append-only phase evidence. Core/Hadoop/build policy and the frozen review queue remain unchanged.
COMMANDS RUN: Exact argv, times, exit codes and log paths are retained in evidence/5d/commands.json. No worker ran sbt; coordinator serialized every build.
TEST RESULTS: fourth-targeted exit 0: 3 owner cases plus 31 independent cases passed. Earlier failures remain retained and are explained in repairs.md. Full gate remains pending at this checkpoint.
VALIDATION RESULTS: Fixed HTTPS Responses endpoint, redirects disabled, bounded body/deadline; closed structured output and locally validated evidence; actual provider model/usage preserved; durable approval-scoped token/spend reservation before dispatch and cross-process lock; unknown failures remain charged; fake/live cache separation; canonical held-out exclusion before scoring; typed decisions, accepted links and complete constraints; explicit runtime receipt/state-path/config binding. The real approval binding probe passed without credential access or HTTP.
ASSUMPTIONS: Wire bytes plus framing allowance conservatively estimate input reservation; this is not exact tokenizer accounting. Usage exceeding reservations stops later calls. Selected model is an alias; no dated snapshot is invented.
RISKS: Synthetic tests do not establish actual provider compatibility, identity accuracy, calibration or human-review completion.
MANUAL ACTION REQUIRED: Actual human review exports remain pending; no generated fixture is counted as a human label.
BLOCKED-ON OWNER: Coordinator for remaining gates.
BLOCKED-ON EVIDENCE: Naturally eligible disjoint real demo evidence, full deterministic gate, runtime credential availability and authorized provider evidence.
NEXT GATE: Finish approved supplement qualification and offline CLI verification, freeze the source, run sbt check, then execute any eligible bounded pilot. User alone launches external review. No 5E, commit or push.


## 5D final technical handoff — external prerequisites pending

STATUS: BLOCKED-ON external prerequisites; offline implementation and technical gates passed.
OWNER: Coordinator; entity-resolution, dataset and independent test owners have stopped.
WORK ORDER: User-authorized Phase 5D provider checkpoint with the separately approved $1 pilot and bounded demo supplement. No 5E.
FILES CREATED: New adapter/demo code, owner/independent tests, bounded supplement scripts and provenance, two durable completed inputs, and evidence/5d receipts. Full paths and hashes are in review-inventory.json.
FILES MODIFIED: ER README, CLI routing and existing leakage-anchor accessor visibility; append-only phase reports; current freeze/inventory/reviewer prompt. No core, Hadoop, build, StableIds formula, matching policy or frozen review-data change.
COMMANDS RUN: Exact commands, times and exits are in evidence/5d/commands.json. Six additional offline integrity gates and their outputs are retained in input-integrity-gates.json. Sole actual public acquisition was the coordinator's bounded command; no model call was attempted.
TEST RESULTS: Fresh sbt -batch check exited 0; 424 tests passed (core 129, Hadoop 64, ER 28, independent 199, build 4), zero failures/errors/skips, 53 fresh JUnit reports. Sbt reported 411 seconds and completed 2026-10-16 22:14:50 America/Chicago. Generated test marker renewed after success. The nested injected failure is expected CheckFailurePathSpec coverage. All 556 frozen files stayed unchanged, with no added/missing scoped files. All 33 Python dataset tests passed; all 6 population/retention validators passed. Targeted tests separately passed 3 owner + 31 independent.
VALIDATION RESULTS: Original queue/split/generation binding/page/guide/input-retention manifest hashes remain identical. Original v3 data and prepared bytes pass validation. Seed-only admission 79/79, zero eligible. Optional acquisition: 7 HTTP attempts, 171,680 bytes, 6.6141 seconds; 20 newly observed works including 8 exclusions; 12 OpenAlex + 14 Crossref ingested. Completed preparation retained outside target; durable replay input/candidate hashes are 3dffec0a31f2cf29781bdbe6da4c1f9046cbec98bccde112b86cb7c101a1c055 and 3fb51d1ac08d167ae142dbd7b64ca2dd31564bc5c05ec3c0552adbd8461d0b94. Canonical admission excludes 70 of 93 candidate pairs before scoring, admits 23, and finds 0 eligible. Actual prepare-live-demo CLI and hashed export proof passed. Actual model calls 0, actual model spend $0.00; no runtime credential lookup or approval-ledger creation occurred.
ASSUMPTIONS: Input reservations use wire bytes plus framing allowance, not exact tokenizer counts; actual provider usage is separate and overruns fuse further calls. Model selection is an alias, with actual provider model retained only if observed.
RISKS: Live provider compatibility remains unverified. No real-model, identity-accuracy, calibration, blocking-recall or human-review result exists. The convenience supplement does not establish held-out performance; unobserved leakage remains possible.
MANUAL ACTION REQUIRED: User confirmed “Not yet” for saved review checkpoints. All 240 initial human reviews remain pending (40 development + 200 held-out), with 60 reserves separate. Use the unchanged blind page and repaired queue; return original checkpoint paths for validation/import. Naturally eligible disjoint real evidence is needed before a model call; any acquisition expansion requires a new concrete approved scope.
BLOCKED-ON OWNER: User for actual human review exports; future explicitly authorized evidence qualification for the live demonstration.
BLOCKED-ON EVIDENCE: Real human labels and naturally eligible non-held-out real-provider evidence. No credential availability is inferred or requested while eligibility is zero.
NEXT GATE: User-launched independent read-only review of implementation/readiness. An implementation APPROVE does not satisfy external prerequisites or authorize 5E. No reviewer, commit or push was launched.


## 5D B1/B2 repair — final technical handoff

STATUS: COMPLETE blocker implementation and observed technical verification; user-launched external recheck pending. Broader 5D remains blocked on human reviews and eligible real-provider evidence.
OWNER: Entity-resolution-engineer (B1), dataset-engineer (B2), independent test-engineer, coordinator (evidence/builds). All workers and builds stopped.
WORK ORDER: Fix only user-supplied external 5D blockers B1/B2. User requested chat-only reviewer prompt; no prompt file created/restored.
FILES CREATED: IndependentLiveCredentialPreflightSpec.scala; repair evidence under evidence/5d-repair/ and selected original-byte snapshots under history/5d-initial-review/.
FILES MODIFIED: Source delta binds exactly 15 modified scoped files plus one new independent test file, no removals, against reviewed 556-file freeze. ER changed credential preflight, reservation check, service delegation and owner tests/docs; dataset changed explicit retention purpose, related tests/docs and only descriptive fields in two demo manifests. Independent tests add service recovery and update the exact safe direct-post error expectation. Coordinator reports/freeze/inventory updated for real repairs.
COMMANDS RUN: Exact argv/cwd/environment/timestamps/exits in evidence/5d-repair/commands.json; separate six-validator receipts in input-integrity-gates.json. Serialized sbt runs: before-fix, targeted, full-check. Dataset owner's commands/output are b2-verification.txt. No network/provider calls or actual credential reads occurred.
TEST RESULTS: Before-fix: seven executed tests failed on unchanged reviewed ER production. After-fix target: 4 owner +40 independent tests passed. Fresh sbt -batch check: exit 0, 434 tests passed (core 129, Hadoop 64, ER 29, independent 208, build 4), zero failures/errors/skips, 54 fresh JUnit reports. Sbt reported 412 seconds and completed 2026-10-17 13:21:56 America/Chicago. Generated marker renewed after passing suites. All 557 frozen files unchanged, zero additions/missing during gate. Nested injected failure is expected CheckFailurePathSpec coverage. All 37 Python tests and six population/retention validators passed.
VALIDATION RESULTS: B1 full JDK header preflight captures a credential once before reservation; local missing/malformed/supplier failures return CREDENTIAL_INVALID / LIVE_CREDENTIAL_UNAVAILABLE_OR_INVALID with zero attempts, unchanged persisted budgets and no fuse. Recovery uses the same approval/ledger without reset. Retries reuse prepared transport. Exhausted-budget/no-eligible/disabled credential laziness and uncertain-dispatch conservative accounting/fusing remain tested. B2 new retention requires explicit purpose; both demo manifests declare development-demo, not frozen review/gold/held-out evaluation. Legacy 5C manifest remains byte-identical (c51963569827ceaba35d1f816a918afecd32a547725ba2b1bb63aa38d49e8556). Only purposeKind/purpose/ownership changed in demo sidecars; payloads, inventories, run IDs, source/completion/run-manifest bytes and blind review assets are unchanged. Proofs: source-delta.json, protected-inputs-proof.json and b2-metadata-proof.json.
ASSUMPTIONS: JDK header validation defines header syntax; it does not establish account/model access. Existing wire-byte reservation heuristic is unchanged.
RISKS: Real-provider compatibility remains unproven. N1 and N3–N8 were intentionally left alone; B1's required credential redaction necessarily covers the shared direct-transport boundary described in N2, with no separate nonblocking work. Original 5D evidence stays historical and unchanged; use history/5d-initial-review/source-freeze.json for its prior source binding and current source-freeze.json for the repaired tree.
MANUAL ACTION REQUIRED: User launches independent recheck using the prompt pasted in chat and returns the full verdict. Actual human reviews remain 0/240 (40 development + 200 held-out), reserves 60 separate; actual model calls 0 and spend $0.00. Naturally eligible non-held-out pairs remain 0. Runtime credential availability was not checked.
BLOCKED-ON OWNER: User-selected reviewer for external acceptance; user for actual review checkpoints.
BLOCKED-ON EVIDENCE: External repair verdict; separately real human labels, naturally eligible real-provider evidence and runtime credentials before any future authorized call.
NEXT GATE: Independent read-only B1/B2 recheck. No reviewer was launched. Even APPROVE does not authorize 5E or establish completed 5D/Phase 5 acceptance. No acquisition, label/policy change, commit or push occurred.


## 5D B1/B2 external recheck result

STATUS: External APPROVE for the implemented B1/B2 repair scope, relayed by the user. OWNER: User-launched independent reviewer; coordinator records only. WORK ORDER: Preserve the full verdict in review.md and evidence/5d-repair/external-recheck.txt. FILES CREATED: External recheck transcription. FILES MODIFIED: Append-only review/owner records and current evidence inventory; no source/data change. COMMANDS RUN: Read-only HEAD/freeze verification; all 557 frozen files match, with no additions/missing files. TEST RESULTS: No rerun needed or claimed; retained fresh gate remains 434 passing sbt tests and 37 Python tests. VALIDATION RESULTS: Reviewer explicitly closed B1/B2 and incidentally N2; new O1–O4 and prior N1/N3–N8 remain deferred under the user's instruction. ASSUMPTIONS: External implementation approval is distinct from a human phase decision. RISKS: Real-provider compatibility and identity accuracy remain unverified. MANUAL ACTION REQUIRED: User completes actual reviews and decides whether to accept the blocked 5D checkpoint or authorize a separate concrete next step. BLOCKED-ON EVIDENCE: Human checkpoints, naturally eligible non-held-out real evidence and an observed provider run. NEXT GATE: Human decision only; no 5E, reviewer launch, commit/push or live call occurred.


## 5D actual human-reviewed batch conversion and import — 2026-10-20

STATUS: COMPLETE for label conversion/import; live-demo qualification and final verification are separate pending gates.
OWNER: Dataset engineer for datasets/**; coordinator for existing CLI execution and phase evidence.
WORK ORDER: User confirmed completing all twelve Markdown batches and authorized conversion/import. No 5E or calibration.
FILES CREATED: datasets/scripts/convert_review_batches.py and its feature tests; datasets/entity-resolution/labels/2026-10-20-danny-ai-assisted-v1/ contains checkpoint, validated derivative, exact original archive, conversion receipt, provenance and README. Evidence is under evidence/5d-label-import/.
FILES MODIFIED: Dataset documentation and append-only phase reports. No Scala source, matching policy, queue, split, generation binding or source evidence changed for this import.
COMMANDS RUN: The existing Phase5Main import-labels CLI exited 0. Exact argv, timestamps and output are in evidence/5d-label-import/commands.json and import-labels.txt. Import-integrity verification exited 0.
TEST RESULTS: All 48 Python dataset tests passed at the import checkpoint, including 11 new conversion cases. Final whole-tree verification will be recorded separately after the additional approved demo search.
VALIDATION RESULTS: All 240 initial tasks have one human-selected decision: 83 same, 149 different, 8 uncertain; 17 choices differ from AI drafts. All 60 reserves remain untouched; the importer's missing=60 refers to reserves. Development: 40 reviews, 38 binary and 2 uncertain; held out: 200 reviews, 194 binary and 6 uncertain. All 16 source files are byte-identical to the original drafts folder. All 557 previously frozen files remained byte-identical. Checkpoint SHA-256 69912290a289be76449a3b6514b4f2b0a240e26fcb40991a12b3850127fcbe08; validated derivative 5fbf6f5bdc1d34f7b79e910a07b964b60bdaaf1dfc825de7744b5f684e39e4a6.
ASSUMPTIONS: User confirmation establishes that the checkbox choices are intended human decisions; reviewer identity is self-entered, not authenticated. Original click times were unavailable: the checkpoint explicitly uses conversion time, not fabricated review times.
RISKS: These are human-reviewed AI-assisted labels, not independent blind gold. Twenty-two Comments explicitly attribute external source checks to Claude; those exceeded the original frozen-source-only draft boundary and are retained verbatim as unverified AI assistance, never presented as Danny's own reasoning or silently added to queue evidence. No identity accuracy or calibration is established.
MANUAL ACTION REQUIRED: No initial review is missing. If 40 development and 200 held-out definitive binary labels are required, at least eight additional definitive reviews/adjudications are needed (2 development Work, 1 held-out Work, 5 held-out Researcher); further uncertain answers could increase this. No reserves are automatically activated and no uncertain label is changed.
BLOCKED-ON OWNER: None for import.
BLOCKED-ON EVIDENCE: Live provider demonstration remains separate.
NEXT GATE: Finish the separately approved bounded search and final verification; no evaluation, 5E, commit/push or reviewer invocation.


## 5D separately approved follow-up demo search — 2026-10-20

STATUS: COMPLETE for bounded acquisition; BLOCKED-ON naturally eligible real-provider evidence.
OWNER: Dataset engineer for scripts, tests and population provenance; coordinator for actual HTTP and canonical metadata probes. ER owner supplied read-only admission advice without reading human labels.
WORK ORDER: User explicitly approved one further public OpenAlex search, up to 30 new records, 20 attempts, 8 MiB and 300 seconds, with no paid data, credentials or label-based selection. Original $1/10-attempt model approval is unchanged.
FILES CREATED: datasets/scripts/acquire_screened_demo.py, test_screened_demo.py, datasets/entity-resolution/5d-demo-2026-10-20-screened/** and evidence/5d-followup-demo/**. No new prepared population was needed or claimed.
FILES MODIFIED: Dataset/script README sections and append-only phase evidence. No production Scala, matching policy, source ID, original population, review queue, label decision or retained prepared payload changed.
COMMANDS RUN: Canonical anchor metadata probes and seed-selection receipts, one coordinator-owned bounded acquisition command, unchanged-context proof, new offline population validator and Python tests. Exact argv/timestamps/exits are in evidence/5d-followup-demo/commands.json. Native network approval was used.
TEST RESULTS: Ten new mocked acquisition tests; all 58 Python dataset tests pass. Seven total population/prepared integrity validators pass. Final sbt result is recorded separately after completion.
VALIDATION RESULTS: Both initial metadata-only screens found zero safe missing-ORCID affiliated OpenAlex author seeds: prior supplement 135 endpoints/12 components/1 held-out-connected component; original frozen input 3,780 endpoints/568 components/541 held-out groups. No labels or comparisons were scored in those screens. The exact user approval was for a general new public CS search; the initial existing-seed restriction was a coordinator implementation strategy. strategy-update.json records its replacement by two fixed topic queries, with any actual observed author-neighborhood queries capped at four. No user decision was rewritten. Actual search: 2 HTTP 200 attempts, 43,664 response bytes, 1.3677 seconds, 10 distinct new records, 0 accepted ingestion records, 0 selected authors/neighborhood requests. All ten passed year/size checks but failed the unchanged CS venue filter. No pagination, refill, replacement query or budget reset occurred. Both actual acquisition stages together observed 30 distinct works, made 9 requests and transferred 215,344 bytes in 7.9818 recorded acquisition seconds.
ASSUMPTIONS: Raw topic results are not domain admission or identity proof. Canonical held-out exclusion remains mandatory before scoring.
RISKS: This bounded search did not obtain any new admissible demo evidence. It establishes neither provider compatibility nor identity accuracy.
MANUAL ACTION REQUIRED: User decides the next 5D checkpoint after inspecting this result; no further acquisition is implied.
BLOCKED-ON OWNER: No implementation owner remains blocked.
BLOCKED-ON EVIDENCE: Naturally eligible non-held-out real evidence and an observed real-provider response.
NEXT GATE: Final deterministic verification and user review. No reviewer was invoked, no model call occurred and spend is $0.00. Runtime credentials were not accessed; no approval ledger/cache state was initialized. No 5E, commit or push.

The new stage's four ingestion source payloads are identical to the prior already-prepared context (OpenAlex comparison uses actual native-ID keyed JSON facts; the other three are byte-identical). outcome.json and unchanged-context-proof.txt record this. The existing canonical supplement result remains 93 candidate pairs, 70 excluded before scoring, 23 admitted and zero eligible. The newly returned excluded records never entered Hadoop or scoring. No new snapshot hash, canonical clearance or prepared-run result is invented; use prepared/68c2b012-6d04-4eef-a7bf-5ca31706d895 and the prior retained admission proof. The unused planning hadoop-config.json and prepare-demo.py.txt were not executed.


## 5D final imported-review checkpoint — 2026-10-20

STATUS: COMPLETE for all 240 review imports, authorized bounded follow-up search and deterministic verification; BLOCKED-ON real-provider evidence for the overall 5D exit.
OWNER: Coordinator with dataset and read-only ER-owner handoffs; all workers/builds stopped.
WORK ORDER: User-authorized conversion/import plus the additional bounded public search.
FILES CREATED / MODIFIED: Current review-inventory.json lists exact tracked/untracked/deleted paths and hashes; source-delta.json isolates this work from the accepted repaired 5D checkpoint. No reviewer prompt file was restored.
COMMANDS RUN: Retained exact argv and outputs under evidence/5d-label-import/ and evidence/5d-followup-demo/.
TEST RESULTS: 434 sbt tests and 58 Python tests passed; seven integrity validators passed. 54 fresh JUnit reports, zero failures/errors/skips, final 615-file freeze valid. Startup README-only correction is disclosed in repairs.md and test-report.md; no production, test, label or population bytes changed during the full check.
VALIDATION RESULTS: Imported all 240 initial AI-assisted human choices: 83 same, 149 different, 8 uncertain. 17 AI-suggestion overrides, 60 reserves untouched. Original source archive, conversion-time semantics and 22 explicitly AI-attributed unverified external-source comments are preserved. Additional acquisition made 2 requests, returned 10 new records, transferred 43,664 bytes and added zero admissible observations; no further queries were made. Existing context remains zero eligible.
ASSUMPTIONS: User confirmation governs the selected choices; import is structural validation, not reviewer authentication or an accuracy result.
RISKS: These labels are AI-assisted rather than independently blind. Eight uncertain choices remain excluded from binary gold. The bounded searches do not establish provider compatibility.
MANUAL ACTION REQUIRED: Inspect the retained import summary; decide the blocked 5D checkpoint and any further explicitly scoped work. No extra reviews or new search are silently authorized.
BLOCKED-ON OWNER: None for completed implementation/import.
BLOCKED-ON EVIDENCE: Naturally eligible non-held-out demo pair and observed real-model response.
NEXT GATE: Human checkpoint decision and independent review of new import/search changes as appropriate. The original $1 approval remains unconsumed: actual provider attempts 0, spend $0.00; runtime credentials untouched, no approval state initialized. No overall 5D/Phase 5 acceptance or 5E advancement is inferred. No reviewer, commit or push was triggered.
     1	
     2	
     3	## 5D decision-attribution correction — 2026-10-20
     4	
     5	STATUS: COMPLETE for the attribution record; the independent-review finding on search query relevance remains open.
     6	OWNER: Reviewing session at the user's explicit direction (“I want you to change it, that's fine”), a disclosed departure from one-writer/reviewer separation; see prompt.md.
     7	WORK ORDER: Record the user's statement that danny set every final checkbox, including all 22 Claude source-check tasks.
     8	FILES CREATED: datasets/entity-resolution/labels/2026-10-20-danny-ai-assisted-v1/decision-attribution.v1.json (22 rows; 17 differ from the AI draft, 5 Comments say "Switched same -> uncertain"; 4 development, 18 held out); evidence/5d-attribution/source-delta.json.
     9	FILES MODIFIED: The label README (attribution section, corrected seventeen-change description); append-only prompt.md and owner-report.md sections.
    10	COMMANDS RUN: One offline Python generator that read the queue, draft, provenance and checkpoint and created the attribution file with exclusive create. No sbt, tests, network, model call or credential access.
    11	TEST RESULTS: None run; this changes JSON/Markdown provenance only.
    12	VALIDATION RESULTS: Generator asserted 22 rows, 17 AI-draft differences and 5 "Switched" Comments. checkpoint.json, validated-labels.json, provenance.v1.json, conversion-report.json and source/ are unchanged and their hashes are bound in the attribution file.
    13	ASSUMPTIONS: The attribution is self-attested by the user, not authenticated.
    14	RISKS: All 17 differences from the AI drafts went from uncertain to definitive (13 held out, 4 development) after Claude external checks whose evidence was not retained. Labels remain human-reviewed, AI-assisted, not independent blind gold; later evaluation should report with and without these 22 pairs. Correction to earlier wording: the 5D import sections describing "17 AI-suggestion overrides" and import-proof.json's humanDecisionOverrides=17 are historical; read them together with this attribution. source-freeze.json (615 files) predates this change and no longer matches the label README or the new attribution file; a refreshed freeze is needed at the next gate.
    15	MANUAL ACTION REQUIRED: Decide whether to authorize fixing and re-running the topic search (sort-order defect).
    16	BLOCKED-ON OWNER: dataset-engineer for the search query fix and test.
    17	BLOCKED-ON EVIDENCE: Naturally eligible non-held-out demo pair and an observed real-provider response.
    18	NEXT GATE: Refreshed source freeze and fresh independent recheck. No 5E, commit or push.


## 5D B2 discovery-ordering root cause — correction to the prior search conclusion

STATUS: External B2 blocker accepted for repair; no external closure claimed yet.
OWNER: Dataset engineer (query/test/history-continuity repair); coordinator (append-only evidence and execution).
WORK ORDER: User-supplied high-severity B2 plus new explicit bounded-rerun approval in evidence/5d-search-repair/user-rerun-approval.json.
FILES CREATED: evidence/5d-followup-demo/root-cause-b2.json and evidence/5d-search-repair/ receipts.
FILES MODIFIED: Append-only owner/review/prompt/repair records and dataset README note; current script/test repair. Original outcome.json, responses, ledgers, executed script and population manifests remain historical and unchanged.
COMMANDS RUN: Retained response metadata inspection; new regression against old code failed as expected (10 passed, one behavioral failure); repaired targeted suite passed 15 tests. Exact commands and outcomes are in evidence/5d-search-repair/commands.json.
TEST RESULTS: Discovery URL regression observed publication_date:asc instead of relevance_score:desc before repair, then passes with explicit descending relevance. Additional cases preserve historical exact-script validation and verify cumulative history continuity without resetting or double-counting copied context.
VALIDATION RESULTS: The old two queries matched 323,411 and 467,092 works but explicitly requested oldest first. This displaced relevance ranking and selected unrelated repository records. The prior ten venue exclusions are real, but the query design caused the poor retrieval. That search does not establish an absence of eligible CS evidence; the zero-eligible claim is limited to the particular retained prepared populations. The coordinator's earlier evidence-blocked wording must not be read as exhaustion of available CS evidence.
ASSUMPTIONS: Relevance ordering improves retrieval design but does not guarantee eligibility. Optional narrower text scope was not required for this minimal sort repair.
RISKS: Naturally eligible evidence and provider compatibility remain unproven until measured.
MANUAL ACTION REQUIRED: No new search approval is needed: the user explicitly approved this separate corrected stage, within 30 returned records, 20 attempts, 8 MiB and 300 seconds, no credentials/paid data; the receipt predates the HTTP command.
BLOCKED-ON OWNER: Coordinator for final preparation/admission/gates; no independent recheck yet.
BLOCKED-ON EVIDENCE: Final frozen verification and user-launched B1/B2 recheck.
NEXT GATE: Finish corrected stage qualification, refresh freeze, run deterministic gates, and return the independent recheck prompt. No real model call, reviewer launch, 5E, commit or push is implied.


## 5D B1 attribution / B2 search repair — final verified handoff

STATUS: Implemented and verified; external B1/B2 recheck pending. Overall 5D provider-evidence gate remains unfulfilled.
OWNER: Dataset engineer for source/tests/retention documentation; coordinator for phase evidence and serialized execution. All workers/builds stopped.
WORK ORDER: User-supplied B2 and B1 procedural clarification, plus explicit corrected bounded-rerun approval. No nonblocking repair or later phase.
FILES CREATED: New relevance-v2 raw acquisition stage; exact development-demo prepared/f22f1a12-c7be-43af-b470-d4f4e244ca9d retention; evidence/5d-search-repair receipts/proofs.
FILES MODIFIED: Dataset query/test and appended dataset/prepared README notes, append-only phase records, current freeze/inventory. Relative to the prior 615-file freeze: 127 additions, five existing paths changed, zero scoped removals. Two B1 paths predated this repair at user direction; protected-proof.json verifies the full current 23-file label tree unchanged. Existing Scala, core, Hadoop, build, matching policy, frozen review set, checkpoint, validated labels, provenance and original sources were not changed.
COMMANDS RUN: Exact command argv/environment/times/exits in evidence/5d-search-repair/commands.json. Separate retention commands are recorded in the dataset owner handoff and tested by standalone retention validation.
TEST RESULTS: Before-fix 11 tests ran: 10 passed, one new URL regression failed behaviorally. After repair 15 targeted acquisition tests passed. All 63 Python tests and nine integrity validators passed (the prior seven plus the corrected raw stage and new prepared input). Fresh sbt -batch check exit 0: 434 tests (core 129, Hadoop 64, ER 29, independent 208, build 4), zero failures/errors/skips, 54 fresh JUnit reports. Sbt reported 410 seconds, completed 2026-10-20 20:45:46 America/Chicago. Expected injected-failure output is build verification coverage. Generated marker renewed. All 742 frozen files remained unchanged from the pre-build freeze.
VALIDATION RESULTS: Corrected acquisition: 3 HTTP 200 attempts, 14 distinct returned works, 5 new ingestion records, 75,738 bytes, 2.2322 seconds; cumulative 44 works/12 attempts/291,082 bytes/10.214 seconds, with no reset/double count. User approval predates every new HTTP request. New prepared input is explicitly development-demo, 60 files/1,444,292 bytes. Target and durable canonical-admission proofs are byte-identical: 101 candidates, 78 excluded before scoring, 23 admitted, zero eligible; held-out pairs scored 0. B1 attribution SHA remains af88956efd996abf8ca6bd9f440d706bf5d651950ee0a02025a29358fa9b2e9b.
ASSUMPTIONS: The user's attribution is self-attested, not authenticated; external source checks remain AI-assisted and unretained. Eligibility is measured only for these bounded inputs, not all public CS evidence.
RISKS: Real-provider compatibility and identity accuracy remain unproven. The old date-ordered search is transparently qualified as flawed retrieval; original historical artifacts remain unchanged.
MANUAL ACTION REQUIRED: User launches a fresh independent read-only session to assess B1 and B2; it must not approve artifacts it authored. Return the complete verdict.
BLOCKED-ON OWNER: None for implemented repair.
BLOCKED-ON EVIDENCE: External recheck; separately, naturally eligible non-held-out evidence and real-model response for overall 5D.
NEXT GATE: User-launched independent B1/B2 recheck. No actual model call, runtime credential access, live-state initialization, reviewer invocation, 5E, commit or push occurred. No additional acquisition or approval reset is implied.


## 5D focused Michael Benedikt search — bounded result

STATUS: Bounded search and CS-input qualification complete; final deterministic gate pending. Real-provider demonstration remains blocked for this input.
OWNER: Dataset engineer (/root/phase5d_focused_dataset) for new dataset artifacts; coordinator for HTTP, unchanged Hadoop, canonical admission and phase evidence. The initially assigned dataset worker stopped at a usage limit before tests; the replacement became the sole writer. Read-only ER owner advised execution without reading labels. No reviewer was invoked.
WORK ORDER: The user explicitly replied “go ahead” to the focused-search proposal, then “pleaes continue”. Exact numerical approval and fixed plan were recorded before HTTP in evidence/5d-focused-demo/user-approval.json and search-plan.json. The earlier $1 model approval remains unchanged.
FILES CREATED: acquire_author_focused_demo.py and test_author_focused_demo.py; derive_focused_cs_population.py and test_focused_cs_population.py; immutable raw focused acquisition, separately derived CS-only population, and development-demo retained preparation 88e3a197-6155-4936-8cf5-e0357cd73208. Phase receipts and admitted-only diagnostics are under evidence/5d-focused-demo/.
FILES MODIFIED: Append-only dataset/prepared README sections and phase reports; final freeze/inventory. No ER/core/Hadoop/build source, matching policy, frozen review population, human decision or attribution changes.
COMMANDS RUN: Exact argv/environment/start/end/exit retained in evidence/5d-focused-demo/commands.json. Root alone ran actual HTTP. Existing unchanged Hadoop pipeline ran first on raw venue-filter output; source inspection caught false positives before any ER call. A separate CS-only preparation then completed. The raw target-only run 22101f00-19ca-492e-94dc-1dcd017e52b8 is not the qualifying input and was never scored or retained as such. The CS-only run 88e3a197-6155-4936-8cf5-e0357cd73208 was retained explicitly as development-demo.
TEST RESULTS: Fifteen focused acquisition tests and six domain-slice tests added; all 84 Python tests pass. Twelve offline population/prepared validators pass. Full sbt result follows separately.
VALIDATION RESULTS: Actual acquisition used six HTTP 200 attempts, five author-profile rows and 21 work rows (26 metadata records total, including every duplicate/exclusion), 218,664 bytes and 5.3543 seconds. No pagination, refill, extra search, credentials or paid-data service. Cumulative history: 65 distinct work IDs, 5 distinct author-profile IDs, 70 returned work rows +5 profile rows =75 metadata rows, 18 attempts, 509,746 bytes and 15.5683 recorded acquisition seconds. Prior unique-work totals are not misrepresented as total rows.

Seven works initially passed the inherited substring venue filter. Inspection found five particle-physics repository entries whose label “Institutional Repositories DataBase (IRDB)” contains database. domain-inspection.json discloses this false positive. Before ER, the new offline CS slice excludes repository sources and requires a CS-venue match on conference/journal sources. It retains the two actual PODS works and the exact single Crossref seed; all original records and identifiers remain unchanged. The raw acquisition script, manifest, original responses and all excluded records are preserved. The slice makes zero requests and references, rather than adds to, parent counters. This is required qualification of this new focused input, not a rewrite of historical populations or a nonblocking legacy repair.

Canonical target and durable replay are byte-identical: six candidate pairs, all six admitted, zero held-out-overlapping pairs, zero eligible. Three Work pairs are hard DOI conflicts; one Researcher pair is accepted through an observed exact ORCID; two Researcher pairs remain unresolved with name-only supportive evidence, unavailable comparable affiliation/coauthor context and scores approximately 0.9 and 1.0. No rule, threshold, identifier, source evidence or label was weakened to manufacture eligibility. All classifications are retained for admitted pairs only. Classified/excluded pair intersection is computed from actual pair-ID sets, not a hard-coded zero.
ASSUMPTIONS: OpenAlex lookup profiles are discovery hypotheses, not verified identity or ingested author evidence. The user’s original label attribution remains self-attested and unchanged. Model documentation was checked with the OpenAI Docs skill; official docs do not prove account/model access or live schema compatibility.
RISKS: This bounded zero-eligible result is local to these inputs, not exhaustion of public CS evidence. No provider compatibility, accuracy, calibration or held-out evaluation is established.
MANUAL ACTION REQUIRED: None for this authorized bounded search; further acquisition or a changed eligibility/policy scope requires a new explicit decision.
BLOCKED-ON OWNER: None for completed dataset/admission work.
BLOCKED-ON EVIDENCE: Naturally eligible non-held-out evidence and an observed real-provider response for overall 5D.
NEXT GATE: Final deterministic check and user review of this checkpoint. No credential lookup, provider dispatch, live-state initialization, model spending, reviewer launch, 5E, commit or push.


## 5D focused-search final handoff

STATUS: COMPLETE for authorized bounded acquisition, offline CS slice, exact retention and verification; overall 5D live-provider exit remains blocked.
OWNER: Coordinator; all dataset/ER workers and builds stopped.
WORK ORDER: Latest user “go ahead” and “pleaes continue”; exact limits are retained in evidence/5d-focused-demo/user-approval.json.
FILES CREATED/MODIFIED: See current source-delta.json and review-inventory.json. No reviewer prompt file was restored. No prior human decision or historical acquisition was rewritten.
COMMANDS RUN: Retained in evidence/5d-focused-demo/commands.json.
TEST RESULTS: 434 sbt tests, 84 Python tests and 12 integrity validators passed. All 898 final source/data/test/config hashes unchanged throughout the complete gate. 54 fresh JUnit reports, zero failures/errors/skips; sbt reported 410 seconds, completed 2026-10-20 21:28:34 America/Chicago.
VALIDATION RESULTS: Actual focused stage used 6 HTTP attempts, 26 returned metadata rows (5 author profiles +21 works), 218,664 bytes, 5.3543 seconds. Raw seven venue matches include five disclosed repository false positives; a separately manifested no-network slice excluded those before ER, retaining two PODS works and the exact original Crossref seed. Canonical target/durable replay yields 6 admitted candidates, no held-out overlap, zero eligible. Three work DOI conflicts, one researcher exact-ORCID acceptance and two insufficient-evidence researcher pairs are documented individually. All labels/attribution and policy/thresholds/IDs unchanged. Actual model calls 0, spend $0.00; runtime credentials untouched, no approval state initialized.
ASSUMPTIONS: Eligibility is local to the bounded qualified input. User attribution remains self-attested; labels remain AI-assisted rather than blind gold.
RISKS: Another real-provider result cannot be claimed or fabricated from this ineligible input. New code/data has no independent external verdict yet; prior B1/B2 APPROVE is not widened.
MANUAL ACTION REQUIRED: User decides the next checkpoint. No further search, matching-rule change or advancement is implied.
BLOCKED-ON OWNER: None for completed authorized work.
BLOCKED-ON EVIDENCE: Naturally eligible non-held-out pair and real-provider result for overall 5D.
NEXT GATE: User checkpoint decision; external review only when launched by the user. Stopped before further acquisition, policy change, provider call, 5E, commit or push.


## 5E limited deterministic/fake evaluation — observed handoff

STATUS: COMPLETE for authorized limited execution; external review pending, overall Phase 5 acceptance open.
OWNER: Coordinator; ER engineer owns evaluation API/cohort support, test engineer owns six independent cases, dataset engineer supplied read-only provenance audit. Native IDs and results: evidence/5e/owner-handoffs.json.
WORK ORDER: User-authorized limited 5E; preserve human labels and existing matcher/config/policy; real-provider requirement explicitly pending.
FILES CREATED: evidence/5e/ observed commands, bindings, predictions, eight reports, development sensitivity, exclusion manifest, replay/protected proofs, summary, manifest and compact source inventory; two independent Scala specs.
FILES MODIFIED: ER Evaluation/ReviewCommands/ReviewReadinessSpec/README; phase source freeze/inventory and append-only reports. No dataset/core/Hadoop/build/matcher/policy/config/label changes.
COMMANDS RUN: Exact argv, cwd, JAVA_HOME/SBT_OPTS, start/end/exit in evidence/5e/commands.json and individual receipts. Three full offline resolution passes, three prediction preparations, eight evaluations, two development sensitivities, Python discovery, 12 validators and final sbt -batch check.
TEST RESULTS: Final targeted 7 owner + 15 independent passed. Fresh full gate 441 passed, zero failures/errors/skips, 56 fresh reports. Core 129, Hadoop 64, ER 30, independent 214, build 4. Python 84 passed; 12 validators passed. Initial sandbox and synthetic fixture failures retained and explained in evaluation-report.md. Nested injected failure is expected CheckFailurePathSpec coverage.
VALIDATION RESULTS: All 900 source files frozen throughout prediction/evaluation/full gate; 804 protected source/data files unchanged including complete label tree. 17 export parts replay; all 300 queue predictions agree; 8 reports independently recounted. Primary held-out 194 binary: TP 57, FP 0, FN 15, TN 122; precision 100%, recall 79.2%, F1 88.4%, decisive coverage 48.5%. Without 22 assisted: 181 held-out binary, TP 51, FP 0, FN 8, TN 122. Full results/evidence: evidence/5e/evaluation-report.md and evaluation-manifest.json.
ASSUMPTIONS: Human choices/attribution are self-attested and AI-assisted, not independent blind gold. Observed matching behavior is only for the frozen convenience population.
RISKS: 8 uncertain, unretained external source checks, no global/blocking recall, uncalibrated policy, residual leakage/common-name risk and no real-provider evidence. Empty LLM/bibliographic paths remain null/no-data.
MANUAL ACTION REQUIRED: User-selected independent review and return of complete verdict.
BLOCKED-ON OWNER: External reviewer selected/launched by user; no implementation owner blocker at this handoff.
BLOCKED-ON EVIDENCE: External verdict; real-provider evidence remains open for overall 5D/Phase 5 rather than being silently waived.
NEXT GATE: Stop for user-launched review. No commit, push, Phase 6 or reviewer invocation.


## Final Rice-team bounded attempt — verified blocked provider checkpoint

STATUS: COMPLETE for authorized bounded work; BLOCKED-ON real-provider evidence for overall 5D / Phase 5.
OWNER: Coordinator for HTTP/Hadoop/canonical/CLI/build execution and reports; dataset-engineer for new datasets/scripts and retention; test-engineer for read-only independent counter/eligibility checks; ER owner supplied read-only feasibility advice.
WORK ORDER: User-approved final targeted attempt: 30 returned rows, 20 HTTP attempts, 8 MiB and 300 seconds; no data credentials or paid data; original $1 model approval unchanged. No refill, fallback or nonblocking repairs.
FILES CREATED: New Rice acquisition script and 13 tests; separately manifested 15-row response stage; 38-file durable preparation; evidence/5d-final-attempt/ receipts, proofs and report.
FILES MODIFIED: Append-only dataset/prepared READMEs, phase reports and current freeze/inventory. No ER/core/Hadoop/build/policy/config/label/evaluation artifact changes.
COMMANDS RUN: Exact argv/environment/start/end/exit in commands.json. Two public queries; unchanged Hadoop; target/durable canonical selection; prepare-live-demo (no network); 97 Python tests; 14 validators; sbt -batch check.
TEST RESULTS: 441 sbt tests passed, zero failures/errors/skips, 56 fresh JUnit reports. Core 129, Hadoop 64, ER 30, independent 214, build 4. All 97 Python tests and 14 validators passed. All 959 frozen source files remained unchanged throughout the gate.
VALIDATION RESULTS: Two HTTP 200 responses, 15 rows, 12 distinct works, 3 ingested, 112,270 bytes, 1.4782 seconds. Eleven admitted, zero excluded, zero eligible. Two unresolved Researcher scores of 0.6933333 are in-band but coauthor overlap of 0.2 fails the supportive threshold of 0.8; other candidates accept or conflict earlier. Target/durable proofs identical; 38 retained files / 204,212 bytes. All 1,261 runtime class/resource hashes unchanged. All 111 approved 5E artifacts and all human choices remain unchanged; historical 5E freeze retained exactly as before-source-freeze.json.
ASSUMPTIONS: Runtime evidence establishes only this bounded population; no real account/model compatibility or identity accuracy.
RISKS: Fixed catalog excludes an observed legitimate CACM record; no global absence claim. Provider requirement still open, credentials untested and no approval state initialized.
MANUAL ACTION REQUIRED: Human checkpoint/continuation decision; independent reviewer only when user launches it.
BLOCKED-ON OWNER: None for authorized bounded work. Human owns continuation and acceptance.
BLOCKED-ON EVIDENCE: Naturally eligible non-held-out pair and observed real-provider response; current 0 attempts, $0.00 spent.
NEXT GATE: Stop acquisition. No policy changes, commit, push, Phase 6 or reviewer launch. Explicit authorization needed before any further scope.

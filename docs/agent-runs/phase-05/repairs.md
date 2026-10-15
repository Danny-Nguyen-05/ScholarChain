# Phase 5 repairs

## Subphase 5A — coordinator-routed audit consistency repair

STATUS: COMPLETE for source repair; execution evidence is in test-report.md.
OWNER: `/root/phase5a_domain` for core implementation/tests; `/root/phase5a_test` for separate adversarial tests; `/root` assembled this record.
WORK ORDER: While checking the 5A deliverables, the coordinator observed that adjudication metadata was permitted on a non-LLM final decision path. This is a shared audit-contract consistency issue, not a returned external reviewer finding.
FILES CREATED: None specifically for this repair; the independent suite is part of the 5A test lane.
FILES MODIFIED: New `ResolutionValidation.scala`, `ResolutionContractSpec.scala`, `IndependentResolutionContractSpec.scala`, and `modules/core/README.md` within their respective owners' paths.
COMMANDS RUN: Owner-reported `git diff --check` exit 0 and test declaration inspection; subsequent actual Scala commands/results are retained in test-report.md.
TEST RESULTS: Owner and independent tests require adjudication metadata iff the final path is LlmAdjudicated, reject final LLM CONFLICT, and permit accepted/rejected/unresolved LLM outcomes only with an unresolved pre-adjudication record. No pre-repair executable failure is claimed; the original issue was observed statically.
VALIDATION RESULTS: Public API fields and six serialized fixtures did not change. Core documentation also requires the future export manifest to bind the complete grouping-constraint bundle hash to run/input/policy; current structural validation cannot prove exporter completeness.
ASSUMPTIONS: Metadata describes a validated completed adjudication. Adapter failures without validated metadata remain unresolved with reasons in later 5B implementation.
RISKS: Full matching precedence, strict provider-response validation and manifest IO remain later-subphase work.
MANUAL ACTION REQUIRED: User-selected independent 5A review after the frozen gate.
BLOCKED-ON OWNER: External reviewer/user for checkpoint review.
BLOCKED-ON EVIDENCE: No external verdict returned yet.
NEXT GATE: Complete observed verification, supply external reviewer prompt, and stop before 5B.

## Subphase 5A — independent test fixture compilation repair

STATUS: COMPLETE.
OWNER: `/root/phase5a_test`; coordinator assembled this record.
WORK ORDER: Repair only the independent test fixture after its first actual compilation failed.
FILES CREATED: None specifically for this repair.
FILES MODIFIED: `tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentResolutionContractSpec.scala`.
COMMANDS RUN: The scheduled independent formatting/classpath/targeted command first exited 1, then exited 0 after repair; exact command and logs are in test-report.md.
TEST RESULTS: Seven independent tests passed after the test-local variable `note` was renamed `fixtureNote` to avoid the inherited ScalaTest Notifier member. The failed compiler output is retained in evidence/5a/independent-targeted-compile-failure.txt.
VALIDATION RESULTS: No production source changed; public contracts and serialized fixtures unchanged. The tester formatted only its own tests/** territory.
ASSUMPTIONS: This is implementation/test development evidence, not an external reviewer finding or verdict.
RISKS: Broader runtime matching behavior remains later scope.
MANUAL ACTION REQUIRED: User-run external review of the final 5A scope.
BLOCKED-ON OWNER: External reviewer/user.
BLOCKED-ON EVIDENCE: External review verdict pending.
NEXT GATE: Frozen integrated gate and external review; no 5B advancement.


## Subphase 5A — external B1 namespace/value/entity repair (in progress)

STATUS: BLOCKED-ON — owner implementation and fresh verification pending.
OWNER: `/root/phase5a_domain` core; `/root/phase5a_er` authority agreement/module README; `/root/phase5a_test` independent regression tests and serialized verification; coordinator evidence only.
WORK ORDER: User supplied independent REQUEST-CHANGES with one blocking finding B1 and nine explicitly nonblocking observations. Full returned text/provenance is in review.md. Fix B1 only within5A, retain deferred observations, rerun targeted/full gates against a new freeze, supply user-run external recheck prompt, then stop.
FILES CREATED: Pre-repair b1-repair-start.json and history/5a-initial-handoff/ retain the original baseline/diff/inventory/prompt. Current changed files will be enumerated after owner handoffs.
FILES MODIFIED: Only owner-approved core authority contract/validation/tests/docs, ER authority documentation and independent tests, plus coordinator evidence.
COMMANDS RUN: Initial git status/HEAD check; bounded Python comparison verified all140original frozen file hashes unchanged before any repair. Exact regression/gate commands/results will be retained in test-report.md.
TEST RESULTS: Pending executable pre-fix regression and post-fix targeted/full checks.
VALIDATION RESULTS: Domain/ER agreement narrows resolution hard-authority namespaces to explicit closed doi/arxiv(work) and orcid(researcher), requires existing StableIds canonical forms and entity compatibility. Unknown aliases/casing fail closed; canonical namespace wire codes are explicit. DBLP/OpenAlex native IDs remain observation bindings; OpenAlex author IDs remain hypotheses. Semantic Scholar/repository URL authority requires future validated namespace semantics/normalizers; no source additions or5Bidentifier algorithms now. Version-bearing arXiv assertions fail closed while original versioned observations remain preserved for a named5Bcomparison policy.
ASSUMPTIONS: Existing lowercase canonical grouping fixture may serialize identically under strict typed codec; preserve/report byte equality rather than fabricate a wire change. B1 acceptance excerpt in supplied review is truncated; reproduced verbatim and interpreted from complete defect/impact description, not invented missing wording.
RISKS: Deferred nonblocking items N1–N9 are retained below; none is claimed repaired by B1. No5Bauthorization or independent recheck verdict exists.
MANUAL ACTION REQUIRED: User runs fresh recheck prompt after verification. N6 ownership was proposed via async question at B1start; that pending status is superseded by the later explicit user approval recorded below. Silence was not treated as approval.
BLOCKED-ON OWNER: Domain/ER/test owners, then user-selected external reviewer.
BLOCKED-ON EVIDENCE: Executable regression, canonical typed contract tests and fresh full gate/new freeze.
NEXT GATE: B1 repair and verification, external5Arecheck, then stop. No5Bimplementation.

### Nonblocking observation disposition

| ID | Required owner / timing | Disposition |
| --- | --- | --- |
| N1 | domain API + ER config; before larger-scale component use in5B | Deferred: indexed validated constraint handle and per-component work limits/large-bundle test. Current behavior fails closed; B1 does not claim performance repair. |
| N2 | domain + ER policy;5B | Deferred: tighten path/outcome/score rules and calibration-artifact semantics with behavior tests. |
| N3 | domain; later shared-contract maintenance | Deferred: existing new enums' case-name wire convention remains fixture-pinned. New B1authority enum uses explicit stable wire codes, without rewriting other enums/pair IDs. |
| N4 | ER input bridge (+domain if sharedAPI needed);5B | Deferred: canonicalize/reject source-native reference aliases before observation-key lookup/dedup. |
| N5 | domain;5B strict-input contract design | Deferred: unknown-field rejection for resolution JSON; pre-existing generic CoreJson behavior unchanged. Closed new namespace enum does reject unknown namespace values. |
| N6 | human-approved ownership before5Blink-export freeze | Resolved by explicit user answer: "Approve the proposed ownership". Phase6spark-engineer owns canonical group construction and deterministic representative selection in modules/spark/** using Phase5acceptedlinks/conflictconstraints; domain-engineer owns shared contract changes. No implementation or constitutional file change now. |
| N7 | ER input bridge;5B | Deferred: explicit diagnostics/counts for all5ineligible pairs, including3profile/work cross-entity pairs; no fabricated researcherpair conversion. |
| N8 | ER schema/policy (+domain if sharedfield needed);5B | Deferred: explicit rules-fired/LLMreason-code mapping and required candidate/input-field references. |
| N9 | ER exporter manifest;5B | Disclosed, accepted for5A: bind complete constraintbundle hash/run/input/policy in exportmanifest. No new bundlefields required in B1. |

### N6 explicit user ownership decision

Question presented by coordinator: "For N6, I recommend the Phase 6 spark-engineer own canonical group construction and deterministic representative selection in modules/spark/**, using Phase 5’s accepted links and conflict constraints. The domain-engineer would own any shared contract changes. Approve that ownership assignment?"

User answer (verbatim): "Approve the proposed ownership".

This assigns exactly one implementation owner and one shared-contract owner within existing artifact territories. It does not authorize Phase6implementation, change constitutional files or approve5A/5Badvancement. Future work orders/README references must use this explicit ownership; no historical human decision file was rewritten.

### B1 source and targeted verification handoff

Domain/ER owners agreed the closed authority set before writes. Independent tests ran against unchanged production first:10tests,7passed,3B1failures,exit1. This demonstrates the reported mixedcaseORCIDABCbypass and invalid namespace/value acceptance. After repair, core13/13 and independent11/11 targeted tests passed, all zero failures/aborts/skips; exact commands/loghashes in evidence/5a-b1/targeted-summary.json.

Core changed only the authority enum/assertiontype, entity/canonical-value validation and validation-before-comparison, plus constructor/test/doc compatibility. New four-test ResolutionAuthoritySpec covers canonicalvalues/strictwires/entitymeaning/transitiveconflicts. Independent four B1tests cover rawJSON namespacealias/unsupportednamespace/wrongentity/valuevariants/arxivbaseversion boundaries without importing owner fixtures. No source normalizers or existing StableIds changed.

The reviewed canonical grouping JSON was not cosmetically regenerated: strict typed serialization intentionally produces exactly the same lowercase doi wire. Its unchanged SHA25686f3d22ed906457570b453d36bf20d4d1e87ca5262e270d6454f3fe7d5bde070 and successful actualScala fixture roundtrip demonstrate compatible canonical output. Malformed/freeform namespaces are now rejected. This fulfills the fixture acceptance purpose without inventing a byte change.

User-approved N6ownership is named in core/ERREADMEs. N1–N5/N7–N9remain deferred as the external reviewer classified them. No owner claims B1closed by independent recheck; that verdict is pending.

A new141file freeze was captured after formatting, source-freeze.json SHA256af669a977e5e87a4040feff1f9cebc54c83ec79528875bc444e08d4397f08e01. b1-repair-source-delta.json lists8changed/new source/doc/testpaths versus b1-repair-start.json, no other implementation changes. Fresh fullcheck is running with no writers active; original236testgate remains historical evidence.

### B1 verification complete — independent recheck still pending

STATUS: COMPLETE forrepairandobservedverification; B1closureawaits externalrecheck.
OWNER: Domain/ER/testowners, coordinatorassembled.
WORK ORDER: B1narrowrepair plus userapprovedN6documentationonly.
FILES CREATED/MODIFIED: Eightsource/doc/testpathslisted b1-repair-source-delta.json; retainedlogs/summary under evidence/5a-b1/.
COMMANDS RUN: Exact targeted/full commands in test-report.md and targeted-summary.json; allpost-fix exits0. Pre-fixexit1expected3regressionsretained.
TEST RESULTS: Core13targeted+independent11targetedpass; final244testfullgatepass,zero failures/errors/skips.
VALIDATION RESULTS:141frozenhashesunchanged,23freshJUnitreports,markerafterpassing; unchangedcanonicalgroupingfixtureactualtypedroundtripverified. Originalreviewedhandoffarchived beforechangingmanifests/diff.
ASSUMPTIONS: Unknownaliases/casing/noncanonicalvalueinputs failclosed ratherthan silentlyrepairing/normalizing them insidegroupguard; sourceingestionowns explicitnormalizationlater.
RISKS: N1–N5/N7–N9remainnonblockingfollowups; N6approved/documented. Neither owner nor coordinator suppliesindependentAPPROVE.
MANUAL ACTION REQUIRED: Userrunsfresh externalrecheckandreturnsverdict; explicit5Badvance stillneeded.
BLOCKED-ON OWNER: User-selectedexternalreviewer/user.
BLOCKED-ON EVIDENCE: Recheckverdictnotyetreturned.
NEXT GATE: External5Arecheckthenstop.


## Subphase5A — B2repair / N10coverage / N11wording (in progress)

STATUS: BLOCKED-ON — newsource-groundingrepairandfreshverificationpending; B1CLOSEDbyuser-suppliedexternalrecheck.
OWNER: domaincore/context/tests/docs; ERauthority/sourcefieldagreementandmoduleREADME; independenttestengineertests/**;coordinatorphaseevidence/serializedverification.
WORK ORDER: Fullnewreviewinreview.md. FixB2canonicalassertionsmustmatchactualendpointsourcefacts;includeN10policy-freecoveredprofileownORCIDcoverageandN11supersededN6pendingwording. NoN1–N5/N7–N9scopeexpansion,nolaterphaseimplementation.
FILES CREATED: b2-repair-start.json;history/5a-b1-recheck/retainsoldfreeze/diff/inventory/prompt/delta. Source/evidencedeltawillbeenumeratedafterrepair.
FILES MODIFIED: Ownedcore/independenttests/moduledocsonlypluscoordinatorevidence.
COMMANDS RUN: InitialHEAD/status;all141previoussourcehashesconfirmedbeforeanyrepair. Before/afterregression/gatepending.
TEST RESULTS: Previous244testgateishistoricalpre-B2evidence,notfreshrepairvalidation.
VALIDATION RESULTS: N11earlierpendingwordinginprompt/repairsmarkedexplicitlysupersededbyrecordeduserapproval; nohumanstatementorquotedreviewrewritten. N6remainsapproved,noPhase6implementation.
ASSUMPTIONS: Sourcefactcanonicalcomparisoniscarriedconsistency,notanLLMornewmatchpolicy. Sourcefactsandfixturesmustbehonest; syntheticIDpositivefixturesmustactuallycarrytestedidentifiers.
RISKS: Narrowgroundingmustpreservecontradictorysourcefactsandnotallowselectiveassertionstoeraseknownconflicts. Grounding/coverageproposaltobereviewedbeforecorewrites.
MANUAL ACTION REQUIRED: Afterfreshverification,user-runexternalrecheckandreturnverdict;5Bstillnotauthorized.
BLOCKED-ON OWNER: domain/testowners,thenuserexternalreviewer.
BLOCKED-ON EVIDENCE: ExecutableB2/N10regressions,source-boundvalidator,correctedfixtures,newfreeze/fullgate.
NEXT GATE: B2repairverification,externalrecheckprompt,STOP.

### B2/N10 executable pre-fix reproduction and agreed consistency scope

Coordinatornativeexecutedindependent14testpre-fixsuiteonunchangedcore:exit1,11existingtests pass,3newtests fail. ActualwrongprofileORCID,contradictoryDOIandmissingknownprofileassertionbypassesretainedinevidence/5a-b2/. Domainwritegoaheadonlyafterthatprocessstopped.

Agreedminimalguard: canonicalclosedassertionmustgroundinthevalidatedendpointsourcefacts AND everyrecognizedsupportedcanonicalhardfactofeachcoveredendpointmustbeexplicitlyasserted. This closesN10andtheanalogousselectiveDOI/Mentionomission; doesnotbecomeanERscoringpolicy. Workdoi/arxivbase/recognizedobservedidentifierrolesandCrossrefkey; actualmentionobservedOrcid; profileownOrcid; ORCIDworkactivityobservedDoi/selfworkreferences areeligiblefacts. Malformedrecognizedfactsfailclosed. Unknownnamespaces/sourceLinksremainobservations; nofactminting, nofetching.

ORCIDrelationshiplimit: selfreferencesmaygroundownworkIDs; related-onlypart-of/version-of/unspecifiedreferencesremainweaksourceevidence. IfpreferredobservedDoiisexplicitlybackedonlybynonselfmatchingreferences, failconsistencyinsteadofdiscardingorupgradingit. LegacytypedpreferredDOIwithnoretainedmatchingreferencecanstillgrounditsownfield. Versionedarxivsourcecanbindcanonicalbaseunderexplicitgrounding-onlyrule;assertionmustremainbasecanonical. Oldpositivetestsassertingabsentarxiv/foreignORCIDmustbecorrectedbyactualsyntheticrecordfacts,notspecialcaseexceptions.

### B2/N10 source handoff and targeted verification

Domainownerimplementedprivatecontextsourcefactgroundingandconstraintsassertion-match/all-factscoverage,withoutpublicAPI/schema/StableIds/sourceformat changes. Sourcefactsvalidatetheactualsource/native/snapshotendpointbeforelookup. Allcanonicalrecognizedfactsretainedso conflictingfacts cannot disappear bysubsettingassertions. ProfileownORCIDandactualmemberobservedOrcidgroundresearchers;worksusedoi/arxivbase/recognizeddeclaredroles/CrossrefDOIkey; ORCIDworkactivitiesuseownpreferredDOIandselfreferences,withrelated-onlypreferredmetadatafailclosed. Unknownidentifiersremainobservations.

N10covered-profileomissionisfixedbythesameknownfactcoverageandexplicitlytested. N11supersededpendingN6approvalwordingclarifiedonlyincoordinatortext; actualuserdecisionquotedunchanged. N1–N5/N7–N9remainnonblockingfollowups; exportercompletenessstillmanifest-boundfuturework.

Owner20targetedtests(9contract,4authority,7newgrounding)pass; independent17targetedtests(11prior,3pre-fixB2/N10regressions,3extendedsourcegroundingcases)pass. Firstafter-fixindependentrunwas16/17:theoldcannotLinkfixtureemptiedprofileassertionsandwascorrectlyrejected. Testerremovedonlythatfixtureoverride,retainedsourcefacts,andreran17/17pass.No productionrulewasloosened. Exactcommands/outputs/loghashesretainedinevidence/5a-b2/targeted-summary.json.

OldpositivearxivassertionswerecorrectedbyactualsyntheticrecordarxivfieldsandcompleteDOI/arxivassertions. ForeignORCIDpositivefixturesnowcarrysourcetrueORCIDs. No inventedID is portrayedasobserved. CanonicaloldgroupingfixturehasgenuineDOIassertionsandremainsunchanged; actualScalafrozenroundtrippasses.

New142filefreezeSHA256cba054febf408a19e421c7eef060b48372c4037fedffa107a6893eadfdba8202;8changed/newsource/doc/testpathsversusb2-repair-start.jsonlistedb2-repair-source-delta.json. Freshfullgateinprogress;nofinalpassclaimyet.

### B2/N10 technical repair verification complete; N11 clarified

STATUS: COMPLETE forrepairandobservedgate; externalrecheckclosurepending.
OWNER: domain/ER/testownerswithcoordinatorevidence.
WORK ORDER: B2grounding+N10coverage+N11supersededpendingwordingonly; B1alreadyindependentlyCLOSED.
FILES CREATED/MODIFIED: Eightsource/doc/testpathslistedb2-repair-source-delta.json;coordinatorreview/evidenceartifactslistedreview-inventory.json.
COMMANDS RUN: Before-fixregressionexit1(11pass3fail),post-fixcoreexit0(20pass),independentrepeatexit0(17pass),fullsbtcheckexit0(257pass),postgatecollectorexit0validtrue. Exactrawresults/testcountsintest-report.md.
TEST RESULTS:20coretargeted+17independenttargetedpass;freshfull257pass,0failure/error/skips. Independentinitialpost-fix16/17oldfixturecoveragefailureandtest-onlyfixretained; noprodrulerelaxation.
VALIDATION RESULTS:142frozenhashesunchanged,24freshJUnitreports,markerafterallpassing. Source-groundedcanonicalassertionsandcompleteknownsupportedfactcoverageverifiedbypositive/negativefixtures. ExistingcanonicalgroupingDOIfixturewireunchangedandactualroundtripvalid.
ASSUMPTIONS: Completeknownfactcoverageonvalidatedsuppliedobservationsisdistinctfromexternalauthenticity/exportmanifestcompleteness; latterfuturebindingunchanged.
RISKS: N1–N5/N7–N9remaindeferred;N6approvedunchanged. N10repaired;N11earliercoordinatorpendingwordingmarkedexplicitlysupersededwithoutrewritinguserdecision.
MANUAL ACTION REQUIRED: Userrunsfresh5AB2/N10recheckpromptandreturnsfullverdict.
BLOCKED-ON OWNER: User-selectedreviewer/user.
BLOCKED-ON EVIDENCE: Externalrecheckpending;owners/coordinatordonotselfapprove.
NEXT GATE: ExternalrecheckthenSTOP;5Bstillunauthorized.

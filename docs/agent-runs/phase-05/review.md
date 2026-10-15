# Phase 5 external review

Current status: returnedrecheckCLOSEDB1andREQUESTEDB2; B2/N10repair/fresh257testverification ready foruser-runrecheck. N11wordingclarified. No newrecheckverdictinferred; historicalreportsretainedbelow.

## Subphase 5A

STATUS: BLOCKED-ON — user-selected external review not yet performed or returned.
OWNER: User-selected independent read-only reviewer; coordinator only assembles this handoff.
WORK ORDER: Review the coherent 5A contract/readiness deliverable after the frozen gate. The coordinator has not launched, selected or impersonated a code reviewer.
FILES CREATED: None by a reviewer.
FILES MODIFIED: None by a reviewer.
COMMANDS RUN: No reviewer commands or builds claimed.
TEST RESULTS: Owner/test-engineer evidence is recorded separately in test-report.md; it is not a reviewer verdict.
VALIDATION RESULTS: Pending.
ASSUMPTIONS: The user will paste the supplied prompt into their preferred independent reviewer and return the full verdict.
RISKS: Test success does not establish factual identity accuracy, human labels, live provider evidence or Phase 5 acceptance.
MANUAL ACTION REQUIRED: Run the supplied external review prompt and return its full verdict. A returned APPROVE still requires explicit authorization before 5B.
BLOCKED-ON OWNER: User / external reviewer.
BLOCKED-ON EVIDENCE: No external review verdict has been supplied.
NEXT GATE: External 5A review; route blockers within 5A and request fresh external recheck if needed. No later-subphase work is authorized.

The complete prepared prompt is retained in `reviewer-prompt.txt` and displayed in full in the coordinator handoff. `review-inventory.json` lists all changed/untracked files and their hashes; the inventory excludes only its own recursive content hash. All builds/workers have stopped. No reviewer has been launched and no verdict is inferred.


## Subphase 5A — user-supplied external review, REQUEST-CHANGES

Provenance: supplied directly by the user in this conversation after the initial handoff. Reviewer identified itself as an independent read-only user-launched Claude Code session. No native reviewer ID was supplied; none is invented. The coordinator did not launch the reviewer. This section transcribes the returned report and does not convert it into acceptance. The acceptance-check text in B1 was incomplete in the supplied message; it is preserved as received.

### Returned report (verbatim)

Independent review: ScholarChain Phase 5, Subphase 5A

Verdict: REQUEST-CHANGES. There is one blocker and nine non-blocking observations. All the claimed evidence checked out. The blocker is a small fix in core contract validation.

STATUS: COMPLETE (review). Verdict for implemented 5A scope: REQUEST-CHANGES (1 blocker).
OWNER: Independent read-only reviewer (user-launched Claude Code session; not manager-invoked).
WORK ORDER: Review 5A per docs/agent-runs/phase-05/prompt.md and reviewer-prompt.txt.
FILES CREATED: None in the repository. A scratch path list was written only under the session scratchpad (outside the repo).
FILES MODIFIED: None.

COMMANDS RUN

All were read-only inspection. No builds, tests, probes, installs, fetches of datasets or provider calls.

- git status / git diff / git ls-files --others.
- Read all of the following:
  - control files and the Phase 4 human-gate and accepted-commit files
  - prompt.md and the plan
  - all changed source, tests and fixtures
  - the entity-resolution (ER) README and contracts
  - the core README diff
  - the related existing contracts: Records.scala, Enums.scala, DomainValidation.scala, StableIds.scala, CoreJson.scala
  - every Phase 5 report and evidence file
  - the Phase 4 export framing under target/phase4-runs/fda6168a…
  - datasets/scripts/acquire_samples.py, to check what its --mode regenerate does
- shasum -a 256 and a Python hashlib comparison of all 140 entries in source-freeze.json and all 40 hashed entries in review-inventory.json.
- Recomputed the full tracked and untracked source diff (excluding phase-05/) and hashed it against implementation.diff.
- WebFetch of the course README: the Phase 5 section, the entity-linkage policy, D07, the rubric, and Phase 6 inputs.

TEST RESULTS

I did not run any tests. The retained evidence is consistent:

- Report hashes: the SHA-256 values for source-freeze.json, full-check.txt and full-check-summary.json match the reported values.
- Plan copy: prompt.md lines 36–490 are identical to /Users/danny/Documents/plan/phase5.md, whose hash matches baseline.json (5dfddeb2…).
- Ownership: build.sbt changed only in independentTests.dependsOn, by the build-engineer. modules/core/** was written by the domain-engineer, modules/entity-resolution/** by the ER engineer, tests/** by the test-engineer, and phase-05/** by the coordinator. .claude/**, AGENTS.md, CLAUDE.md, docs/agents.md, .gitignore and project/** are unchanged. No human decision was rewritten.
- Real-data compatibility: Phase 4 work exports carry nested authors, so ResolutionValidationContext's mention binding works against real exports, not just fixtures.
- Dataset lane: acquire_samples.py --mode regenerate only verifies committed bytes; it makes no network calls. No dataset files changed.

BLOCKER

B1 — Medium-High: the grouping-constraint conflict guard uses raw, untyped namespace strings

Where: ResolutionContracts.scala:121-126, plus ResolutionValidation.scala:252-263 and 308-312.

The problem. ResolutionIdentifierAssertion.namespace and value are free strings. check(constraints) only requires them to be non-blank and trimmed. checkComponent finds identifier conflicts with groupBy(_.namespace) and compares raw values.

What goes wrong (static reasoning): take a Researcher bundle where A asserts ("orcid", 0000-0002-1825-0097) and C asserts ("ORCID", 0000-0001-5109-3700). B is covered and has no IDs. Then checkComponent(Vector(A,B,C), …) returns Right: a validated component with two different authoritative ORCIDs.

- The same miss happens for "openalex" vs "openalex-author". The existing code already treats those as aliases (DomainValidation.scala:140,817).
- Real ORCID exports already contain free-text namespaces such as "Scopus Author ID".
- Value spellings also go unchecked. URL-form and bare ORCIDs, or DOI case variants, produce false conflicts.
- Nothing checks that a namespace fits the entity type: a Work bundle can assert orcid, and a Researcher bundle can assert doi.

The existing typed IdentifierNamespace enum and the StableIds normalizers are not used.

Impact. Core and ER READMEs both tell Phase 6 to rely on this validator before grouping. As written, a transitive A–B, B–C merge can join conflicting authoritative IDs through a spelling difference: exactly the unsafe merge the course gate forbids ("Exact ID conflicts do not silently merge"). Fixing it after 5B starts emitting v1 data would be a breaking wire change, so it is cheapest now.

Owner: domain-engineer (modules/core/**). ER should confirm which namespaces are authoritative.

Acceptance check:
1. Use a closed, typed namespace. Either reuse IdentifierNamespace, or define a resolution-specific closed set with a documented decision on Semantic Scholar and repository URL.
2. Require canonical values via StableIds: normalized DOI; bare
   - (b) a non-canonical ORCID or DOI value
   - (c) an orcid assertion in a Work bundle
   - (d) A-B-C with conflicting ORCIDs in any accepted spelling
6. Rerun the targeted suites and a fresh sbt check against a new freeze.

Blocks 5A: Yes.

NON-BLOCKING OBSERVATIONS

None of these block 5A. Owners are named; suggested timing is 5B unless stated.

N1 — Medium: checkComponent bound does not bound per-component work (ResolutionValidation.scala:290-327, config.example.v1.json:47; owner: domain-engineer for the API, ER for config)
- The bundle is defined as complete and run-level, but every checkComponent call re-validates the whole bundle.
- That costs O((cannot-links + assertions) × covered endpoints) using Vector.contains, and the member-coverage check is another O(members × endpoints).
- maxConstraints caps the whole bundle, not the component. The planned population (~2,000 works at ~5 authors each, about 10k mention endpoints) exceeds the example maxConstraints=10000. Either every component fails closed, or the caller raises the bound to run size and it stops bounding anything.
- This fails closed, so it is not unsafe.
- Accept when: the bundle is validated once into an indexed handle; per-component checks cost in proportion to the members and their constraints; and a large-bundle test exists.

N2 — Low-Medium: path/outcome rules are under-constrained (ResolutionValidation.scala:169-204; owner: domain-engineer, or ER policy in 5B)
- CONFLICT is allowed on the Scored, ExactIdentifier and DeterministicBibliographic paths. Only HardConflict ⇒ CONFLICT is enforced, which blurs per-path metrics.
- A Scored decision, even an ACCEPTED one, may have confidenceSemantics=Unavailable.
- preAdjudication.decisionPath=Scored is allowed with score=None.
- CalibratedProbability can be declared without binding to any calibration artifact.
- Accept when: either these rules are tightened, or the ER policy loader enforces them, with tests.

N3 — Low: new enums use Scala case names as wire values (ResolutionContracts.scala:16,47,51,55, plus ResolutionIds.pair hashing entityType.toString; owner: domain-engineer)
- Existing core uses explicit EnumCodecs.wire codes; the new enums don't. Renaming a case would change the v1 wire format and every pairId.
- This is mitigated: the roundtrip test pins the fixture JSON and pair IDs. It is a convention inconsistency only.

N4 — Low: context keys use the raw sourceRecordId (ResolutionValidationContext.scala:38-58; owner: domain-engineer or the ER input bridge)
- parseSourceRecordId accepts several spellings of one native record: ORCID with or without a leading /, and OpenAlex as a URL or bare ID.
- The real export uses no slash, while the owner fixture activity uses /.
- Two spellings of one record in a snapshot would become two observations. That evades duplicate-conflict detection and the self-pair check.
- Accept when: the 5B bridge canonicalizes or rejects non-canonical forms, with a test.

N5 — Low: unknown JSON keys are silently dropped (CoreJson.scala:10-20, pre-existing behavior; owner: domain-engineer)
- uPickle's default ignores unknown keys, so v1 resolution records with misspelled or extra fields parse, and decisionId recomputation ignores what was dropped.
- Consider strict reading for scholarchain.resolution.v1.

N6 — Low: canonical-representative ownership is unassigned (core and ER READMEs; owner: human/orchestrator decision)
- Course Phase 6 says "Map Hadoop pair candidates onto canonical researcher IDs". 5A defers representative selection to "the later consuming implementation" without naming an owner, which is an orphan under docs/agents.md.
- Assign it before the 5B link-export design is frozen.

N7 — Low: 5 of the 14 real distinct pairs can't be represented (owner-report.md:52-61, ER README:46-50; owner: ER engineer in 5B)
- The five are: 3 ORCID-profile↔work (cross-entity), 1 employment↔work, and 1 distinction↔distinction.
- The docs specify an explicit skip for non-work activities but don't name the profile↔work cross-entity case.
- 5B needs explicit skip diagnostics and counts for all five.

N8 — Low: course decision-record mapping is not documented (owner: ER engineer in 5B, with domain if a field is added)
- The course requires "rules fired" and LLM output with "candidate IDs, cited input fields, confidence, reason codes".
- How these map onto reasonCodes, decisionPath and evidenceRefs isn't documented, and ResolutionAdjudication has no LLM reason codes separate from the final MatchDecision.reasonCodes.
- Settle this in the 5B strict response schema.

N9 — Disclosed and accepted for 5A: the constraint bundle has no runId or inputEvidenceHash. Binding is deferred to the export manifest. Adding the fields now would avoid a future v2.

ASSUMPTIONS

- Static reasoning about uPickle 4.0.2 defaults (unknown keys ignored, Option as null). The latter is confirmed by the fixture JSON.
- B1's reproduction is static reasoning from the code. The owner or tester must make it an executable test.
- The DESIGN_ONLY contracts are judged only as design examples.

RISKS

- Passing tests show contract consistency only. They say nothing about identity accuracy, calibration, human review or provider behavior.
- The real candidate supply is insufficient (populationStatus=INSUFFICIENT: 6 work/work pairs, 0 researcher pairs). This is honestly reported.
- Core reference validation is structural. Exporter completeness can't be proven by the validator.

MANUAL ACTION REQUIRED

- Return this verdict to the manager.
- The manager routes B1 to the domain-engineer and the matching tests to the domain and test engineers.
- Rerun targeted tests and a fresh sbt check against a new freeze, and supply a fresh external recheck prompt.
- The human decides N6 ownership.
- 5B is not authorized by this review.

BLOCKED-ON OWNER

domain-engineer, for B1.

BLOCKED-ON EVIDENCE

Still needed for B1:
- an executable test showing that namespace/value variants can't bypass checkComponent
- the regenerated grouping fixture
- a fresh full gate

UNVERIFIED GATES

- I did not re-execute any test, sbt, Python or dataset gate; those results rest on the retained logs, which are internally consistent.
- I did not verify the full DBLP, OpenAlex, Crossref and ORCID access and license claims beyond the cited links.

NEXT GATE

B1 repair, observed re-verification, then an external 5A recheck. After that, explicit user authorization is still required before 5B.

Broader Phase 5 acceptance (separate from the 5A verdict)

None of these exist yet, and none were claimed: the 240 human reviews, a gold set or evaluation, calibrated thresholds, a matcher, the review tool, an LLM adapter or live evidence, D07, or Phase 5 acceptance. All belong to 5B–5E and the human gate.


## Subphase 5A — B1 recheck handoff, no verdict yet

STATUS: BLOCKED-ON — user-selected externalrechecknotyetperformed/returned.
OWNER: User-selected independentreviewer; coordinatoronlyassemblespacket.
WORK ORDER: RecheckB1typednamespace/canonicalvalue/entitymeaningrepair, reviewed8source/doc/testpathdelta, regenerated/bytecompatiblefixtureproof, and newfrozen verification. N6ownershipapproved/documented; remaining8observationsstillnonblockingfollowups.
FILES CREATED/MODIFIED: Nonebyreviewer; coordinatorpreparedreviewer-prompt.txt/review-inventory.json andretainedreports.
COMMANDS RUN: No manager-launchedreviewerorreviewerbuilds claimed. Technicalverificationattributedtoowners/coordinator/testengineer separately.
TEST RESULTS: Post-fix13core/11independenttargetedpass,full244testgatepass; thisisnotareviewverdict.
VALIDATION RESULTS: Pre-fix3B1failuresretained;new141filefreezeunchanged;canonicalgroupingfixturetypedroundtripwireunchanged. Exactevidencepaths/hashesinreviewer-prompt.txt/review-inventory.json.
ASSUMPTIONS: Userwillrunfreshrecheck andreturnfullverdict.
RISKS: Broader5Agatesremainpendingreview; no5B–5Eacceptanceorfeaturesclaimed.
MANUAL ACTION REQUIRED: Pastefullpreparedpromptintopreferredindependentreviewer;returnverdict.
BLOCKED-ON OWNER: User/externalreviewer.
BLOCKED-ON EVIDENCE: ReturnedrecheckAPPROVEorREQUEST-CHANGESpending.
NEXT GATE: External5Arecheck;evenAPPROVErequires explicituseradvancebefore5B. Allworkers/buildsstopped.


## Subphase 5A — user-supplied B1 recheck verdict: B1 CLOSED, B2 REQUEST-CHANGES

Provenance: user supplied a transcript of the original review, reviewer discussion/hook messages, and the completed B1 recheck. The reviewer identified itself as an independent read-only Claude Code session launched by the user; no native reviewer ID supplied. Coordinator did not launch a reviewer. The completed recheck verdict below is transcribed with its B1 assessment table rendered as plain-text rows; earlier pasted hook/config discussion is contextual user-supplied transcript, not manager-executed tests or new implementation authorization. This supersedes the preceding pending-recheck state, without rewriting the original review or human gate files.

### Returned B1 recheck report (B1 table rendered as text)

Phase 5A recheck verdict (B1 repair)

Verdict: REQUEST-CHANGES. B1 is closed. I'm reporting one new blocker, B2. It is not a regression from the repair: it was already in the code I reviewed in round 1, and I should have reported it then. It sits in the same conflict guard, so I'm reporting it now rather than letting it through.

STATUS: COMPLETE (recheck). Verdict for the 5A/B1 repair scope: REQUEST-CHANGES. B1 is CLOSED; one new blocker, B2.
OWNER: Independent read-only reviewer, launched by the user in Claude Code.
WORK ORDER: Recheck 5A B1 per the B1 addendum in docs/agent-runs/phase-05/prompt.md and reviewer-prompt.txt.
FILES CREATED: None in the repository.
FILES MODIFIED: None.

COMMANDS RUN

All commands were read-only. I ran no builds, tests or probes.

- Diffed the repaired production and test files against the originally reviewed text in history/5a-initial-handoff/implementation.diff.
- Read ResolutionAuthoritySpec.scala, the independent spec changes, the StableIds normalizers (normalizeDoi, workIdFromArxiv, researcherIdFromValidatedOrcid, normalizeIndexedIdentifier), EnumCodecs.wire, the Fixtures.scala source facts, both READMEs, prompt.md §B1, repairs.md, review.md, and the evidence/5a-b1 logs.
- Rehashed every entry in the source freeze and review inventory, recomputed the full tracked and untracked diff, and compared the inventory with git status -uall.

TEST RESULTS

Not executed by me. The retained evidence is consistent:

- Before the fix: independent-before-fix.txt shows 7 passed and 3 failed, all three of them B1 tests, at 11:22:24.
- After the fix: full-check.txt shows 112, 64, 64 and 4 tests passing and [success] Total time: 398 s at 11:31:58. The summary agrees: exit 0, 244 tests, zero failures, errors or skips.

VALIDATION RESULTS

Each claim below I confirmed myself:

- Freeze: all 141 source-freeze.json hashes match. Against the original 140-file freeze, exactly the 8 claimed paths changed and nothing was removed.
- Inventory: all 56 hashed review-inventory.json entries match. The inventory equals git status -uall exactly, in both directions.
- Diff: the live diff hashes to f71e5f60…, which equals implementation.diff.
- Hashes: all five stated SHA-256 values match.
- N6: the user's answer is recorded at repairs.md:64-71. The core and ER READMEs name the owners (modules/core/README.md:93-95, ER README.md:94). No Phase 6 work began.
- Constitution: no constitutional files changed.

B1 assessment: CLOSED

Each part of the original defect is now handled:

(a) Alias or case-variant namespace: ResolutionAuthorityNamespace with explicit wire codes (ResolutionContracts.scala:123-159). EnumCodecs.wire (Enums.scala:268-279) only accepts exact matches, so "ORCID" is rejected when the JSON is parsed.
(b) Non-canonical values: acceptsCanonicalValue requires the value to equal the StableIds normalizer output: a lowercase bare DOI; a bare ORCID with a valid checksum; an arXiv base ID with the version rejected (old-style versioned IDs already fail arxivPattern).
(c) Wrong entity meaning: ResolutionValidation.scala:258-260. The namespace must match both the bundle's entity type and the endpoint's.
(d) A-B-C conflict: groupBy on the closed enum over canonical values (:310-333). Conflicting ORCIDs can no longer hide behind spelling. checkComponent now stops if the bundle itself is invalid.
Executable proof: Before/after evidence. The three failures were real before the fix and pass after it.

Leaving the grouping fixture byte-identical is correct. The new codec still writes "doi", and the Scala roundtrip covers it.

BLOCKER

B2 — Medium: authoritative identifier assertions are not checked against the endpoint's own source observation

Where: ResolutionValidation.scala:252-270 (no context check on assertion values). The repair's tests treat these cases as valid: ResolutionAuthoritySpec.scala:70-73, and the arXiv test added at the end of IndependentResolutionContractSpec.scala.

What the validator misses. It checks the namespace, the value's spelling and the entity type. It never checks that the asserted value is actually an identifier the endpoint's source record carries. The validation context already holds that record and binds the endpoint's carried orcid and workId to it.

Reproduction (static reasoning). Use the independent spec's own setup:
- profile A, whose endpoint and record ORCID is orcidA
- mention B
- profile C, whose ORCID is orcidC

Assert (A, orcid, orcidC) and (C, orcid, orcidC). Every existing check passes: covered, Researcher type, canonical, valid checksum, evidence present. checkComponent(A, B, C) then sees a single ORCID value and returns Right. Two profiles with different ORCIDs are merged.

The same pattern works for works. Assert a DOI or arXiv ID that the source record doesn't carry: Fixtures.work has arxivId = None (Fixtures.scala:186), yet the arXiv assertion 2301.01234 on it validates. The tests treat that as expected behavior.

Impact.
- The guard that the core and ER READMEs tell Phase 6 to rely on can be defeated by a wrong value, not just a misspelled one.
- It accepts identifiers that aren't present in the source. That conflicts with the course rule against creating identifiers that aren't in the candidates, and with "Exact ID conflicts do not silently merge."
- The fix needs no ER authority policy. It is the same "carried consistency" binding that core already applies to workId and orcid.

Owner: domain-engineer for modules/core/**. The test-engineer adapts the independent fixtures.

Acceptance check:
1. check(constraints, context) rejects any assertion whose value isn't present, in the same namespace and after canonicalization, in that endpoint's validated observation:
   - OrcidProfile: must equal endpoint.orcid.
   - Mention: must equal observedOrcid.
   - Work: the record's doi, its arxivId base, or a matching observedIdentifiers entry.
   - OrcidWorkActivity: observedDoi or a matching workReferences entry.
2. Fix the fixtures that currently assert absent arXiv IDs, either by giving the fixture records real arxivId values or by removing those assertions.
3. Add owner and independent tests that are rejected: (i) the A→orcidC mis-assertion merge above; (ii) a DOI or arXiv assertion absent from the record; (iii) a DOI assertion that contradicts the record's DOI.
4. Rerun the targeted suites, freeze again, and run a fresh sbt check.

Blocks 5A: Yes.

NON-BLOCKING OBSERVATIONS

- N10 — Low-Medium, new (owner: domain-engineer): a covered ORCID-profile endpoint carries its ORCID inside the endpoint itself. If no assertion is made for it, checkComponent ignores that ORCID. Profiles A and C with different ORCIDs and no assertions can therefore be grouped with mention B. The README says the validator doesn't "infer absent constraints" (modules/core/README.md:88-90), so this is a disclosed limit, not a blocker. Still, requiring or deriving the profile's own ORCID assertion is cheap, policy-free, and best done together with B2.
- N11 — Trivial, new (owner: coordinator): prompt.md:505 and repairs.md:50 still say N6 approval is "not inferred". Later sections record the actual approval at repairs.md:64-71. Mark the earlier wording as superseded.
- Carried over: N1–N5 and N7–N9 are unchanged and stay non-blocking. The new short-circuit in checkComponent doesn't change N1's cost profile.

ASSUMPTIONS

The B2 reproduction is static reasoning from the code. The owner or tester must turn it into an executable test. ORCID 0000-0001-5109-3700 is the checksum-valid value already used in the passing independent fixture.

RISKS

- Exporter completeness remains a future manifest-binding item.
- Everything here is structural validation only. No identity accuracy, labels or provider behavior is established.

MANUAL ACTION REQUIRED

- Return this verdict to the manager.
- Route B2, and optionally N10, to the domain-engineer and test-engineer.
- After the fix, run a fresh gate and a new external recheck.
- 5B is not authorized.

BLOCKED-ON

- BLOCKED-ON OWNER: domain-engineer, for B2.
- BLOCKED-ON EVIDENCE: executable tests (i)–(iii) showing grounding is enforced, the adjusted fixtures, and a fresh full gate.

NEXT GATE

The B2 repair and its verification, then an external recheck. Explicit user authorization is still required before 5B.

Broader Phase 5 acceptance (separate from this verdict)

None of the following exist yet, and none were claimed: the 240 human reviews, a gold set or evaluation, calibration, a matcher or input bridge, the review tool, an LLM adapter or live evidence, D07, or Phase 5 acceptance.


## Subphase5A — B2/N10 repaired-source recheck handoff (no verdict yet)

STATUS: BLOCKED-ON — user-selectedexternalrechecknotyetreturned.
OWNER: User-selectedindependentreviewer;coordinatorpreparespacketonly.
WORK ORDER: RecheckB2actualsourceidentifiergroundingandN10knownfactcoverage,correctedfixtures,N11statusclarification,andfresh257testgateon142frozenfiles. B1alreadyCLOSEDbyreturnedreview; N6ownershipapprovedandunchanged.
FILES CREATED/MODIFIED: Nonebyreviewer. Coordinatorreports/diffs/hashinventoriesandpromptarehandoffartifacts.
COMMANDS RUN: Nomanager-launchedreviewernorreviewerbuildexecuted. Ownershipandcommandsintest-report.md.
TEST RESULTS: Before-fix3newfailuresreproduced;post-fixcore20/20,independent17/17,full257/257pass. Evidenceisnotanindependentrecheckverdict.
VALIDATION RESULTS:142hashesunchanged;24freshJUnitreports;markerrenewedafterpass. Eightrepairsource/doc/testpathsversusb2-repair-start.json;history/5a-b1-recheck/retainspreviousreviewedstate. Currentreview-inventory.jsonincludesalltracked/untrackedfiles/hashes.
ASSUMPTIONS: Userpastesfreshpromptintopreferredindependentreviewerandreturnscompleteverdict.
RISKS: Other8nonblockingobservationsandalllater-phaseprerequisitesremainexplicit;noacceptanceinferred.
MANUAL ACTION REQUIRED: Runfreshrecheck;returnfullverdict;explicitadvanceinstructionstillneededbefore5B.
BLOCKED-ON OWNER: User/externalreviewer.
BLOCKED-ON EVIDENCE: B2/N10recheckAPPROVEorREQUEST-CHANGESpending.
NEXT GATE: External5Arecheckandstop;allworkers/buildsstopped.

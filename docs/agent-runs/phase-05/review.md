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


## Subphase 5B — external review handoff pending (2026-10-16)

STATUS: BLOCKED-ON external review; this is a coordinator status entry, not a reviewer verdict.
OWNER: User-selected independent reviewer.
WORK ORDER: Read-only review of the implemented 5B deterministic resolution and offline adjudication scope, plus the minimal shared grounding dependency.
FILES CREATED: None by an external reviewer.
FILES MODIFIED: None by an external reviewer.
COMMANDS RUN: No reviewer was invoked by the manager or implementation agents.
TEST RESULTS: Observed owner/coordinator results are in test-report.md and evidence/5b/. They do not constitute independent acceptance.
VALIDATION RESULTS: User supplied “status approved” for 5A and explicitly authorized 5B. A complete external B2/N10 APPROVE report was not supplied; the actual earlier reports remain preserved and no reviewer text has been invented.
ASSUMPTIONS: User launches their preferred reviewer with the final saved/displayed prompt and returns the full verdict.
RISKS: Code and deterministic tests do not establish identity accuracy, calibration, real labels or live provider behavior.
MANUAL ACTION REQUIRED: After the final gate, run the supplied reviewer prompt and return its complete verdict.
BLOCKED-ON OWNER: User-selected reviewer.
BLOCKED-ON EVIDENCE: External 5B APPROVE or REQUEST-CHANGES.
NEXT GATE: External 5B review; repairs if requested. Even APPROVE requires explicit authorization before 5C.


## Subphase 5B external review — user-supplied REQUEST-CHANGES

Provenance: user-launched Claude Code session, reported model Opus 5.5. No manager invocation. Review scope/reading limitations are preserved exactly below. Both blockers are routed; no external closure is inferred.

```text
Verdict: REQUEST-CHANGES. There are two blocking findings and ten nonblocking ones. The gate evidence checks out: all six key hashes and all 170 frozen file hashes match the current tree, the test counts add up to 339, and earlier evidence was archived unchanged rather than overwritten. The blockers are logic problems that the tests don't catch:

1. One DBLP record can stop the whole run. Phase 4 accepts a DBLP DOI link containing % or ? as the record's DOI. The new 5B grounding rejects that same link, and the input step turns that one rejection into a failure of the entire run. This is likely to appear once 5C pulls in more DBLP data.
2. Venue and affiliation produce false "mismatch" scores. Each source names venues in its own ID format. The real-input demo shows venue = 0 for the same DOI publication across DBLP, OpenAlex and Crossref. Under the current policy, no cross-source work pair can then score above 0.9, so the scored accept path (0.95) and the LLM band (up to 0.85) can never be reached.

I didn't fetch the course README from GitHub or read the Phase 1 and Phase 4 gate files; I relied on the plan's summary, and none of the findings depend on them. Complete verdict for the manager:

STATUS: COMPLETE (read-only review). VERDICT for implemented 5B scope: REQUEST-CHANGES
OWNER: Independent read-only code reviewer (user-launched; Claude Code session, model Opus 5.5). Not manager-invoked.
WORK ORDER: Phase 5 Subphase 5B (deterministic resolution + offline adjudication), per
  docs/agent-runs/phase-05/reviewer-prompt.txt; HEAD/5B start 4ac236fcb01825b73635fa4c762a35bed4b362cd, branch phase-5.
FILES CREATED: None.
FILES MODIFIED: None.
COMMANDS RUN (all read-only; no builds/tests/probes/installs/network):
  git rev-parse HEAD; git status --short; git diff [--stat|--numstat] HEAD; git show HEAD:<4 archived evidence files> | shasum
  cat/sed/grep/wc over AGENTS/CLAUDE/docs/agents.md, code-reviewer.md, agent-runs/README.md, plan phase5.md,
    phase-05 prompt/reports, all ER production/resources, core ResolutionValidationContext/Contracts/StableIds excerpts,
    Hadoop DblpExtract/JsonSources excerpts, test case listings
  shasum -a 256 on the 6 key evidence files
  python3 -I (read-only): recompute SHA-256 for all 170 source-freeze.json entries; summarize demo-outputs decisions
TEST RESULTS: Not run by reviewer (prohibited). Retained evidence inspected:
  - full-check-summary.json: exit 0, 339 tests (126+64+14+131+4 = 339), 0 failures/errors/skips, 36 reports;
    full-check.txt ends "[success] Total time: 399 s ... 2:52:47 PM".
  - Tests do not establish identity accuracy, calibration, blocking recall, human review or real-model behavior.
VALIDATION RESULTS (reviewer re-verified, read-only):
  - The 6 key SHA-256 values in the prompt match the files exactly.
  - All 170 source-freeze.json entries match the current tree (0 changed/missing): the reviewed source is the gated source.
  - history/5a-final-handoff/{implementation.diff, review-inventory.json, reviewer-prompt.txt, source-freeze.json}
    are byte-identical to their HEAD versions; owner-report/test-report/review/repairs/prompt are append-only (0 deleted lines).
  - Changed paths stay inside the agreed owners' areas (core: domain; entity-resolution: ER; tests/**: test;
    phase evidence: coordinator). No build/Hadoop/dataset/constitutional/human-gate file changed.
  - Static review confirms: strict marker/manifest/9-success/inventory/digest/UTF-8/JSONL checks on input;
    full (source, record, snapshot) lookups with an optional workId hint; conflict check before exact/bibliographic/
    scored/LLM acceptance and again before link export; LLM eligibility limited to sufficient in-band unresolved
    pairs; disabled mode makes no adapter/cache access; closed response parsing with JSON-pointer field
    checks; cache key = hash of full request (evidence, features, IDs, policy/config/prompt/schema/model/settings);
    exporter checks constraint coverage, assertions and cannot-links; no label/held-out inputs.

BLOCKING FINDINGS

B1 [HIGH, blocks 5B] DBLP `ee` grounding rejects input that Phase 4 accepted, and one bad endpoint aborts the whole run.
  Paths: modules/core/.../ResolutionValidationContext.scala:55-91, 104-111;
         modules/entity-resolution/.../InputLoader.scala:56-62 (any Left from groundedAuthority -> throw inside assemble);
         modules/hadoop/.../DblpExtract.scala:725-726, 987-997; modules/core/.../StableIds.scala:54, 171-179.
  Evidence (static): Phase 4 normalizeDoiLink/normalizeDoi accepts `https://doi.org/<10.x/\S+>` and emits it as
    WorkRecord.doi (e.g. "10.9999/encoded%2fvalue", "10.5555/source?other=10.5555/target", or a DOI with raw
    '<' '>'). In the same accessor call, the preferred `doi` is grounded (Right) while the identical `ee` link is
    rejected (path contains '%', query/fragment present, or java.net.URI fails to parse -> resolverPrefix -> Left).
    ResolutionInput's eager `authority` map throws, so InputLoader.load and the whole CLI run fail (exit 2).
    Tests lock this in as intended: ResolutionAuthorityConsumerSpec.scala:137-152 and
    IndependentResolutionEngineSpec.scala:264-267 (`ResolutionInput.create(...).isLeft`).
  Impact: a valid accepted Phase 4 export cannot be resolved. One record in a 5C DBLP expansion blocks queue
    generation and every later run. The rule is inconsistent (the same DOI is accepted in one field and fatal in the other).
  Required owners: domain-engineer (core grounding consistency); entity-resolution-engineer (failure scope);
    test-engineer (independent probe).
  Acceptance check: a completed Phase 4 fixture whose DBLP record has ee `https://doi.org/10.9999/encoded%2Fvalue`
    (plus a `?` variant and a raw '<' SICI-style variant) passes Hadoop prep. Phase 5 then must not abort the run.
    Either (a) the ee value grounds the same canonical DOI Phase 4 accepted (no invented contradiction), or
    (b) the endpoint gets an explicit per-observation diagnostic, is excluded from every accepting path, and is
    marked in the manifest/constraints so downstream grouping fails closed. Unrelated observations still resolve;
    complete-constraint validation still passes. A real conflicting ee DOI is still retained as a conflict.

B2 [MEDIUM, blocks 5B] Features that compare incomparable representations return a "mismatch" (0) instead of unavailable.
  Paths: modules/entity-resolution/.../FeatureExtractor.scala:164-165 (venue), 111-130 and 155-156 (affiliation);
         src/main/resources/phase5-policy.v1.json:9-12, 17.
  Evidence (executed, retained real-input outputs): evidence/5b/demo-outputs/5b-disabled-demo/work/accepted.jsonl.
    The same DOI publication (DBLP series/sapere/BerkeleyR13, OpenAlex W4254447616, Crossref
    10.1007/978-3-642-31674-6_1) has venue = 0 in all three cross-source work pairs where both sides carry a venue.
    Venue IDs are namespaced per source (DBLP `venue:dblp-booktitle:*`, Crossref `venue:issn:*`, OpenAlex IDs),
    so x != y always yields 0.0. Affiliation takes a Jaccard over a mixed set of ror:/ringgold:/name:/enrichment IDs,
    so the same institution recorded differently scores 0.
  Impact: violates plan §8.2 ("missing evidence must not become ... a negative fact") and the 5A design table
    (README.md:175, "same-kind comparable observations required"). Under the runtime work policy, a perfect
    cross-source pair scores at most (0.5+0.3+0.1+0)/1.0 = 0.9: below accept 0.95 and above LLM band max 0.85.
    Cross-source scored acceptance and LLM eligibility are therefore unreachable, which biases 5C strata and 5E path metrics.
  Required owners: entity-resolution-engineer; test-engineer.
  Acceptance check: venue is unavailable with an explicit missing reason unless both IDs share a comparable namespace
    (or a documented normalized label/ISSN rule applies). Affiliation compares only like-for-like representations
    (ROR to ROR, name to name), and mixed-only evidence is unavailable. Hand-computed independent tests cover a
    cross-source work pair and a mixed-representation affiliation pair. A rerun of the real input shows the
    cross-source venue as unavailable. Policy/feature version or fingerprint changes are recorded.

NONBLOCKING FINDINGS

N-1 [MEDIUM] The deterministic bibliographic rule can merge distinct works.
  ResolutionEngine.scala:81-88, 109-118. Title token-set equality + identical author-name set + same year accepts
  with no venue/type check and no minimum title content. Generic DBLP titles ("Preface.", "Editorial.") by the same
  editors in the same year, or same-year conference/journal versions, are accepted when DOIs are absent; venue
  contradiction is ignored. Owner: entity-resolution-engineer (policy before the 5C freeze); test-engineer.
  Check: two DOI-less "Preface." records with the same editors and year but different same-namespace venues are not accepted.
N-2 [MEDIUM] Cost grows faster than linearly inside the declared limits.
  InputLoader.scala:179-189 (texts.exists per work), 205-220 (works.exists per affiliation/enrichment),
  63-83 (refs(): linear scans plus re-serialize/hash per call, called several times per pair);
  CandidateBuilder.scala:45, 72 (`input.evidence ++ derived` per add, while `derived` grows on every attempt
  including dropped ones, so O(attempts^2)); FeatureExtractor.scala:111-130.
  At the config limits (100k rows, 50k lookups, 100k attempts) this is about 1e9-1e10 operations; fine for 18 pairs.
  Owner: entity-resolution-engineer. Check: indexed lookups/memoized refs, plus a timed synthetic large-input probe
  run by the owner/tester before any 5C scale-up.
N-3 [LOW-MEDIUM] No guard keeps --output/--cache outside the --input run directory (or --input outside --output).
  Phase5Main.scala:38-40; LinkExporter.scala:45-53. Output written under the completed Phase 4 run changes its file
  set (the next load fails the exact-inventory check), which weakens the "no source mutation" claim.
  Owner: entity-resolution-engineer. Check: CLI test rejects nested paths before any write.
N-4 [LOW] Response reason codes are not tied to the outcome. Adjudication.scala:220-231 accepts
  outcome=accept with INSUFFICIENT_EVIDENCE or SUPPORTED_DIFFERENT_IDENTITY. Fix before any 5D live call.
  Owners: entity-resolution-engineer; test-engineer.
N-5 [LOW] The audit catalog labels DBLP ee DOI/arXiv links as repository-url with authority=false
  (FeatureExtractor.scala:21-23, 59-63), while core grounding treats them as hard authority. A conflict caused only by
  an ee DOI has no authority=true row in DecisionDetail.identifiers (the constraint assertions do carry it).
  Owner: entity-resolution-engineer.
N-6 [LOW] `name` returns 0.0 instead of unavailable when a name normalizes to no tokens (FeatureExtractor.scala:136-141).
  Scored rejection needs no evidence sufficiency, so a single available feature can reject (ResolutionEngine.scala:121-130).
  Policy note for the 5C freeze. Owner: entity-resolution-engineer.
N-7 [LOW / policy] Cross-source copies of one paper's author mentions can be accepted only through ORCID:
  samePublication suppresses coauthorOverlap and "context" is a required group. All 6 real Researcher UNRESOLVED
  rows are this case. Conservative and disclosed; record as an explicit 5C stratum / 5E path limitation.
N-8 [LOW] A pair removed for aggregate evidence bytes keeps its per-mention quota, so extra supporting blocks can
  make a pair disappear and still use up the cap (CandidateBuilder.scala:46-53, 83). Owner: entity-resolution-engineer.
N-9 [LOW] A failed write leaves the staging directory behind, and a POSIX rename can replace an empty directory created
  between ensureNew and the move (LinkExporter.scala:225-248). Owner: entity-resolution-engineer.
N-10 [LOW, documentation] Several 5B evidence passages have their spaces stripped (repairs.md 5B observations; the
  owner-report "owner/test handoff" section), which makes human audit hard. Owner: coordinator (rewrite going forward; keep history).

ASSUMPTIONS:
  - Course README (GitHub) was not fetched in this session; requirements were taken from the plan §3 summary.
    Phase 1 authority and Phase 4 human-gate files were not reopened. No finding depends on them.
  - Not every test body was read line by line; test coverage claims were checked by listing cases and targeted greps.
  - DOI forms in real DBLP (percent-encoded / SICI) are offered as plausible triggers. B1 is established by code
    reasoning plus the repo's own tests, not by an executed probe.
RISKS:
  - OpenAlex authorship ORCIDs are hard authority under the approved 5A contract, so an OpenAlex misattribution
    becomes an exact-ID accept. Evaluate this as its own stratum in 5C/5E.
  - Runtime policy is uncalibrated; no accuracy, recall, blocking-recall or live-provider evidence exists.
  - The current sample (18 comparisons) cannot support 40 development + 200 held-out reviews; 5C acquisition is required.
  - Hashes show internal consistency, not authenticity. Arbitrary injected JVM adapters cannot be force-killed (disclosed).
MANUAL ACTION REQUIRED: User returns this verdict to the manager. The manager routes B1 to domain-engineer +
  entity-resolution-engineer (+ test-engineer probe) and B2 to entity-resolution-engineer + test-engineer, reruns the
  affected suites, the full `sbt -batch check` and the real-input CLI runs, then issues an updated reviewer prompt.
  Nonblocking items are at the owners' discretion; N-1 and N-4 are recommended before the 5C freeze / 5D respectively.
BLOCKED-ON OWNER: domain-engineer (B1 core); entity-resolution-engineer (B1 input scope, B2); test-engineer (independent cases).
BLOCKED-ON EVIDENCE: Executed B1 probe on a completed Phase 4 fixture; B2 hand-computed feature tests plus a real-input
  rerun; fresh full gate on a re-frozen tree.
NEXT GATE: Repairs -> fresh verification -> new external 5B review. 5C is NOT authorized by this verdict;
  even a later APPROVE needs explicit user authorization.

Broader Phase 5 acceptance limitations (not 5B blockers): 5C review tool/queue/import/evaluator, bounded acquisition,
40+200 real human reviews, 5D provider selection and live calls, 5E frozen evaluation (precision/recall/F1, coverage,
path breakdowns, threshold sensitivity, representative errors) and final human acceptance are all outstanding.
The manifest does not yet bind code revision/source hashes, which §12 requires for 5E.
```


## Subphase 5B B1/B2 repair recheck — pending user-launched verdict

STATUS: BLOCKED-ON external recheck, not an approval.
OWNER: User-selected independent reviewer.
WORK ORDER: Recheck both external 5B blockers and bounded related repairs against the new frozen source and retained evidence.
FILES CREATED / FILES MODIFIED: No external reviewer has edited repository files. Coordinator prepares evidence only.
COMMANDS RUN: No manager-launched reviewer, reviewer build or reviewer behavioral probe.
TEST RESULTS: Owner/coordinator verification is retained in evidence/5b-repair/ and test-report.md. Tests do not constitute independent acceptance.
VALIDATION RESULTS: The original full REQUEST-CHANGES report and its stated reading limitations remain preserved, with the prior handoff in history/5b-initial-review/. The repaired source must receive a new independent verdict.
ASSUMPTIONS: User will paste the completed prompt into their preferred reviewer and return the full verdict.
RISKS: Generic-title scored acceptance, scaling, quota release and staging/race follow-ups remain nonblocking and disclosed; no accuracy or human-label evidence is claimed.
MANUAL ACTION REQUIRED: Run the external recheck prompt and return its complete verdict.
BLOCKED-ON OWNER: User-selected reviewer.
BLOCKED-ON EVIDENCE: New APPROVE or REQUEST-CHANGES.
NEXT GATE: External 5B recheck; explicit user authorization still required before 5C.

## Subphase 5B repair recheck — external APPROVE received 2026-10-16

STATUS: COMPLETE for external 5B repair review; APPROVE. This supersedes the preceding pending-recheck status.
OWNER: User-launched independent reviewer (Claude Code, Opus 5.5); coordinator records the supplied result only.
WORK ORDER: Record the returned B1/B2 recheck and the user's disposition of nonblocking findings.
FILES CREATED: evidence/5b-repair/external-recheck-approval.txt preserves the complete supplied verdict and subsequent user instruction.
FILES MODIFIED: review.md and repairs.md, append-only receipt records.
COMMANDS RUN: Read-only inspection and evidence-document edits only; no reviewer launch, build, test, acquisition or provider call.
TEST RESULTS: The reviewer inspected retained evidence of 356 passing tests and five pre-fix regression failures; the reviewer did not execute tests. No new test execution is claimed for this receipt.
VALIDATION RESULTS: The reviewer reports all six key hashes and 174 frozen source hashes match. B1 and B2 are CLOSED against their stated acceptance checks; no finding blocks 5B. The reviewer did not fetch the course README or reopen Phase 1/Phase 4 gate files. See the complete supplied verdict for scope and limitations.
ASSUMPTIONS: External approval covers implemented 5B repair scope only; it is not broader Phase 5 acceptance or authorization for 5C.
RISKS: Remaining nonblocking findings stay documented and unfixed per the user's explicit instruction. Their historical recommendations are not new implementation work orders.
MANUAL ACTION REQUIRED: None for 5B repairs. Wait for explicit user authorization before 5C.
BLOCKED-ON OWNER: None for 5B.
BLOCKED-ON EVIDENCE: None for 5B.
NEXT GATE: Explicit user authorization for 5C. The reviewed freeze, inventory and prompt remain the historical review packet; this receipt is a subsequent documentation-only append.

## Subphase 5B — explicit human approval received 2026-10-16

STATUS: COMPLETE for 5B implementation, external review and human approval.
OWNER: Human architect; coordinator transcribes the user's chat decision as evidence.
WORK ORDER: Record explicit human approval separately from the external reviewer's APPROVE.

User decision, verbatim:

> alright I approve the change, now give me a one line commit message for this change

The subsequent request to record this approval was:

> do you need to note for the human review approval?

FILES CREATED: None.
FILES MODIFIED: review.md and owner-report.md, append-only approval receipts. No human-owned gate or accepted-commit file was authored or changed.
COMMANDS RUN: Read-only evidence inspection and documentation edits only.
TEST RESULTS: No new tests run for this documentation-only receipt; retained verification remains 356 passing tests.
VALIDATION RESULTS: Explicit user approval follows the user-supplied independent APPROVE for the 5B B1/B2 repairs. Both blockers are closed. Remaining nonblocking findings remain unfixed per the user's prior instruction.
ASSUMPTIONS: Approval applies to the submitted 5B change. It does not authorize 5C or constitute final Phase 5 acceptance.
RISKS: Known nonblocking limitations remain recorded in the external verdict and repairs.md.
MANUAL ACTION REQUIRED: User handles the requested commit/push; no accepted commit SHA is inferred.
BLOCKED-ON OWNER: None for 5B approval.
BLOCKED-ON EVIDENCE: None for 5B approval.
NEXT GATE: Explicit user authorization before starting 5C.

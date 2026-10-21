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


## Subphase 5C — external review pending

STATUS: Implementation and targeted/browser verification complete; full-gate result follows in final addendum. Independent 5C review is PENDING.
OWNER: Coordinator preparing handoff; independent reviewer remains user-selected and user-launched.
WORK ORDER: 5C only, authorized at clean `phase-5` HEAD `c8342d25ba04dede26af10bedc5a76691824d1ca`.
FILES CREATED / FILES MODIFIED: See `5c-source-delta.json`, final source freeze and review inventory.
COMMANDS RUN / TEST RESULTS: Retained in `test-report.md` and `evidence/5c/commands.json`. No reviewer was invoked.
VALIDATION RESULTS: Real queue/split 40 development +200 held out +60 reserves; 20/20 and 100/100 entity allocation; deterministic replay and actual synthetic browser resume verified. Source population limitations remain explicit.
ASSUMPTIONS / RISKS: Tests and queues are not human labels, calibrated accuracy or live-provider evidence; remaining 5B nonblocking issues remain unfixed.
MANUAL ACTION REQUIRED: User copies the final reviewer prompt into a read-only independent reviewer and returns the complete verdict.
BLOCKED-ON OWNER: User-selected independent reviewer after final gate.
BLOCKED-ON EVIDENCE: Observed full gate and external 5C verdict.
NEXT GATE: External review and any required current-subphase repairs; explicit authorization before 5D. No 5C acceptance is inferred.


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


## Subphase 5C — user-supplied external REQUEST-CHANGES

Provenance: full user-returned independent read-only verdict, not a manager-launched review. The reviewer did not fetch the course README live. The user then instructed: "fix the blockings bugs first for me". This supersedes the earlier pending external-review status; no acceptance is inferred.

STATUS: REQUEST-CHANGES (2 blockers, 8 nonblocking findings)

The 5C work is mostly sound. The claimed hashes, test counts, allocation and blinding all checked out. But two defects should be fixed before you start labeling. Both are cheap to fix now and expensive once 240 human labels exist.

OWNER: code-reviewer (independent, read-only; launched by the user)

WORK ORDER: Phase 5, Subphase 5C readiness review. Sources: docs/agent-runs/phase-05/prompt.md (5C authorization, lines 556–572), /Users/danny/Documents/plan/phase5.md §§10–14 and the pasted reviewer prompt. I read the course README section only as it is summarized in the plan and prompt. I did not fetch it live.

FILES CREATED: none
FILES MODIFIED: none

---

Blocking findings

B1 — High — Human labels are tied to matcher settings that 5D and 5E must change

- Where:
  - ReviewQueue.scala:45-55, 363-366: the queue hash covers ReviewBinding, which includes the policy hash, config hash, prompt hash, model identity, code revision and source hash.
  - ReviewCommands.scala:133-143: the real queue binds modelIdentity = deterministic-fake/abstain-fixture/v1 and the full config fingerprint, which includes the provider, model and spend settings (ResolutionPolicy.scala:255-282).
  - GoldLabels.scala:56-59 and index.html:29: a saved checkpoint must match the exact queueHash.
  - ReviewCommands.scala:155-160, 176-179, Evaluation.scala:157, 293, 313: predictions are refused unless policy, config, prompt, model, code and source all equal the queue's values.
  - modules/entity-resolution/README.md:522 says it outright: a changed policy, prompt, model or code "requires a new binding and a new review/evaluation cycle or an explicit exploratory qualification."
  - IndependentEvaluationAdapterSpec.scala:117-135 tests this behavior as intended.
- Why it breaks: the plan's order is queue → labels → 5D provider/model selection → development calibration (new thresholds) → 5E frozen held-out evaluation. Choosing a real provider changes the model identity and config hash. Calibration changes the policy hash. After either change, prepare-evaluation-predictions and evaluate reject the predictions. Rebuilding the queue with new values changes queueHash, and then both the importer and the page reject your existing checkpoints.
- Impact: the 240 human reviews could never be scored against the calibrated policy or real LLM output. 5E could only report them as "exploratory" or redo them. This contradicts plan §10, which says to freeze the population before scoring and the policy after development calibration.
- Owner: entity-resolution-engineer for the code; test-engineer for the changed independent expectation.
- Acceptance check:
  a. The queue/checkpoint identity binds only what labels depend on: source population, input evidence, candidate population, split, sampling and each task's evidence hash.
  b. Evaluation binds predictions to those same hashes and records the policy, config, prompt, model and code in its own manifest (verified at 5E).
  c. New tests: label a synthetic queue built under policy P0 with the fake model, then evaluate predictions made under P1, a different model identity and a different adjudication config section, with the same input and candidates. This must succeed and record P1 and the new model. A changed input, candidate population or task evidence must be rejected. Replace the expectation at IndependentEvaluationAdapterSpec.scala:117-135.
  d. Regenerate the real queue before any labeling, and re-show byte-identical replay and the 40/200/60 allocation with 20/20 and 100/100 by entity.
- Blocks 5C: yes. Zero labels exist, so this is the cheapest moment to fix it.

B2 — Medium — The input the queue is bound to lives only in ignored target/ and cannot be regenerated

- Where: the queue's inputEvidenceHash 57efd819… is computed over a completion hash (marker plus run manifest) and evidence payloads (InputLoader.scala:236-245, 514). Those payloads embed runId: run:bd424a86-…, which appears 5,299 times in queue.json. The only matching copy is target/phase5c-prep-runs/bd424a86-… (132 MB, of which the export is 47 MB). That directory is gitignored (.gitignore:2) and is the root sbt project's target, so sbt clean would remove it (I did not run that).
- Why it breaks: re-running Hadoop gives a new run UUID, which changes the input hash, the evidence references and the task evidence hashes. prepare-evaluation-predictions (ReviewCommands.scala:161-165) then refuses the input. Phase 4 only promised "logically equivalent" reruns, not byte-identical ones.
- Impact: if target/ is cleaned, 5E cannot produce predictions for the labeled queue. The labels survive, but they become unusable for scoring.
- Owner: needs a human ownership decision. dataset-engineer (datasets/**) is the natural owner for retention; entity-resolution-engineer if it is solved by making the binding independent of the run ID.
- Acceptance check: either keep the exact completed run (export/**, _SCHOLARCHAIN_COMPLETE, run-manifest.json) in a durable, hash-manifested location outside target/, or make the binding independent of the run UUID. Then show that loading from the durable copy reproduces inputEvidenceHash and candidatePopulationHash 9381588e…. Coordinate with B1, since the queue gets rebuilt anyway.
- Blocks 5C: yes.

Nonblocking findings

N1 — Medium — The guide doesn't warn that OpenAlex author IDs and OpenAlex-supplied ORCIDs are provider guesses
- Where: guide.txt:9-14.
- Evidence: 38 of the 120 initial researcher tasks show equal OpenAlex author IDs and equal ORCIDs (from OpenAlex). Five more show only equal OpenAlex IDs. Mention payloads display identityStatus: EXTERNAL_IDENTIFIER_OBSERVED. Meanwhile datasets/entity-resolution/README.md:13-15 records that OpenAlex author neighborhoods contained medical records, i.e. OpenAlex merged unrelated people. The 5B review also asked for OpenAlex-supplied ORCIDs to be evaluated separately.
- Impact: human gold labels may copy provider errors and inflate agreement.
- Owner: entity-resolution-engineer.
- Acceptance check: the guide and page text say these IDs are provider hypotheses, not verified identity.

N2 — Medium-low — A backward clock change can permanently block saving
- Where: index.html:33 stamps each answer with new Date() and doesn't enforce increasing times. index.html:29 (also run on save, line 36) rejects a revision older than the previous one, or any annotation later than the export time.
- Impact: if the system clock steps back between two revisions of the same task, the bad revision stays in history. Every later Save fails, and refreshing loses all unsaved work.
- Owner: entity-resolution-engineer; test-engineer adds a test with a mocked clock.
- Acceptance check: answers keep timestamps in order and a clock regression never blocks Save.

N3 — Low-medium — The real queue has never been loaded in the page
- Evidence: only a 6-task synthetic queue was tested in a browser. A browser-side load depends on JS and Scala hashing the JSON identically. My static scan of the real queue found nothing likely to break that: no floats, large integers, integer-like keys, surrogates or control characters. It does contain 145 non-ASCII strings, which both sides render as raw UTF-8.
- Impact: if the hashes disagree, the page rejects the real queue as altered and labeling can't start. No labels would be lost.
- Owner: test-engineer.
- Acceptance check: a load-only browser probe of the real (rebuilt) queue shows "0 of 240 initial tasks answered", with zero label clicks.

N4 — Low-medium — Two CLI paths have never been executed
- Evidence: prepare-evaluation-predictions and the sensitivity CLI have no test or run. The completion marker, manifest, file-hash and path-traversal checks at ReviewCommands.scala:166-219 are unexercised. Only fromDecisions and an evaluate run with empty predictions are covered.
- Owner: entity-resolution-engineer and test-engineer.
- Acceptance check: CLI tests cover a complete run and the corrupt, partial and traversal cases, before 5E.

N5 — Low — Reserves are counted as "missing" labels
- Where: GoldLabels.scala:107-109 computes missing against all 300 tasks.
- Impact: it reports 60 "missing" even when all 240 initial reviews are done.
- Owner: entity-resolution-engineer.
- Acceptance check: separate counts for initial and reserve tasks.

N6 — Low — One command in the evidence ledger has no exit code
- Where: evidence/5c/commands.json, entry independent-first-target.
- Evidence: the entry still says status: running with no exitCode, but its log shows 17/17 tests passed. The reports don't disclose this.
- Owner: coordinator.
- Acceptance check: record the observed outcome or add an explicit note.

N7 — Low — The script that actually ran the acquisition isn't kept
- Evidence: the v2/v3 manifests bind acquisitionScriptSha256 2c2ad01e…, but no file in datasets/ or docs/ has that hash. The current script is 5861fc79…, and the initial attempt has no script hash at all. The later script changes are disclosed.
- Owner: dataset-engineer.
- Acceptance check: retain those bytes, or state that they can't be recovered.

N8 — Low — Repository size
- Evidence: datasets/entity-resolution is 47 MB, including identical 12 MB response copies in both v2 and v3. The queue and split add another 11 MB of evidence.
- Owner: you decide before committing; then dataset-engineer and coordinator.

---

COMMANDS RUN (all read-only):
- git rev-parse / status / diff, plus sed, cat, grep, find, du, cmp
- shasum -a 256 on the 8 claimed artifacts
- python3 -I scripts that only read JSON, to recompute freeze and inventory hashes and to count queue composition, blinding fields, ID agreement and names/titles recurring across partitions
- No builds, tests, browser, network or writes.

TEST RESULTS: I ran no tests. What I observed in the retained logs:
- full-check.txt ends [success], and full-check-summary.json shows 383 tests, 0 failures/errors/skips, 44 reports.
- The browser-downloaded checkpoint is byte-identical to synthetic-browser-checkpoint.json, which was imported via the CLI with exit 0.

VALIDATION RESULTS (my own read-only checks):
- All 8 claimed SHA-256 values match.
- All 509 freeze files match the current tree, and the queue's sourceTreeHash 79a54bde… equals that freeze.
- The 402 inventory paths equal git status -uall, with no hash mismatches.
- The real queue has 300 tasks: 40/200/60, with 20/20 and 100/100 by entity.
- No prediction, score or label fields appear (the 285 enrichment score fields are all null), and no abstracts are retained.
- All v3 venues are CS venues, years 2018–2024.
- No 5C changes touch core, Hadoop, build or constitutional files.
- From reading the code: the page renders with textContent under a CSP with connect-src 'none', reserves are hidden by default, the importer enforces linear revisions, and the evaluator's denominators follow plan §12.

ASSUMPTIONS: that sbt clean on the root project removes ./target (standard sbt behavior; not executed).

RISKS:
- Process: the disclosed incident where browser automation typed the local HTML path into a ChatGPT conversation. Future runs should use an isolated browser profile.
- The browser test is a manual, agent-driven script (tests/browser/phase5c-review-cua.js), not an automated regression, so future page changes have no automated guard.

MANUAL ACTION REQUIRED:
- Don't start labeling until B1 and B2 are resolved and a new queue is issued.
- Assign an owner for B2 retention.
- Decide on N8 before any commit.

BLOCKED-ON OWNER: entity-resolution-engineer (B1); human ownership decision, then dataset-engineer or entity-resolution-engineer (B2); test-engineer (B1 test change)

BLOCKED-ON EVIDENCE: a rebuilt queue with the decoupled binding, the policy/model-change acceptance tests, proof that the input can be reloaded from durable storage, a fresh sbt check, and an updated freeze and inventory.

NEXT GATE: owners repair → fresh gates → a new reviewer prompt for a recheck. Even after an APPROVE, 5D needs your explicit authorization.

Broader Phase 5 limitations (not 5C defects)

- There are zero human labels; all 240 are pending.
- This is a convenience sample: blocking recall and global identity recall are unmeasured, and nothing is calibrated.
- About 64% of initial tasks (77/120 work, 77/120 researcher) are effectively decided by IDs shown on screen. Per-path metrics for the scored matcher will therefore rest on roughly 86 initial tasks across both partitions.
- Researcher coverage is 110/120 OpenAlex–OpenAlex pairs.
- The queue has no same-publication researcher pairs, so the deferred 5B finding N-7 stays unmeasured; per your instruction it was left unfixed.
- Two common names ("yang wang", "yong wang") appear in both development and held-out tasks. This is residual leakage risk that grouping can't prevent.
- No real provider adapter, live calls, calibration, held-out scoring, 5D/5E or Phase 5 acceptance exists yet.


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


## 5C B1/B2 recheck — user-supplied external review

STATUS: APPROVE (B1 and B2 closed).
OWNER: Independent external reviewer, as reported by the user; coordinator transcribes only.
WORK ORDER: User supplied: "5C external recheck verdict: APPROVE (B1 and B2 closed). Record the full verdict in review.md under 5C B1/B2 recheck, as a user-supplied external review."
FILES CREATED / FILES MODIFIED: No reviewer-created or reviewer-modified files were specified.
COMMANDS RUN / TEST RESULTS / VALIDATION RESULTS: No additional reviewer commands, tests or validation narrative were supplied; do not infer them. The complete verdict text received is preserved verbatim above and in evidence/5c-precommit/external-approval.json. No longer report was attached. This supersedes the preceding pending repair recheck status.
ASSUMPTIONS: User is relaying the external review.
RISKS: Previously documented nonblocking findings remain unless explicitly covered by the new bounded cleanup.
MANUAL ACTION REQUIRED: Complete the user's bounded pre-commit cleanup; user handles any eventual commit.
BLOCKED-ON OWNER / BLOCKED-ON EVIDENCE: None for the supplied external APPROVE; no broader reviewer narrative available.
NEXT GATE: One fresh sbt check after authorized cleanup; stop before 5D. No commit/push or next-subphase authorization inferred.


### Approved cleanup completion

The user-supplied external APPROVE for 5C B1/B2 remains recorded above. The separately authorized pre-commit cleanup and one fresh full gate completed: 390 tests passed with zero failures, all 587 frozen files unchanged. The real repaired queue load-only browser check displayed 0 of 240 answered with zero labels. Evidence and final size are in evidence/5c-precommit/. No new reviewer verdict is inferred or requested; no commit/push or 5D start.


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


## 5D implementation/readiness handoff — no external verdict yet

STATUS: Awaiting user-launched independent review. Coordinator observed 424 passing sbt tests, 33 passing Python tests, six successful data-integrity validators and unchanged 556-file freeze. These are implementation verification results, not self-approval or a completed 5D human/provider gate. The approved supplement still produced zero naturally eligible admitted pairs; actual model attempts/spend remain zero. User replied “Not yet” regarding saved human annotation checkpoints. Human labels and real-provider evidence therefore remain pending external prerequisites under plan §5D.

The full read-only reviewer prompt is reviewer-prompt.txt. No reviewer was invoked. Earlier user-supplied external verdicts and human decisions remain unchanged. An eventual implementation APPROVE cannot authorize 5E or invent real reviews/provider execution.


## 5D user-supplied external review — REQUEST-CHANGES

STATUS: COMPLETE (read-only review). Verdict for implemented 5D code/readiness: REQUEST-CHANGES.

OWNER: code-reviewer (user-launched, independent). Repairs go to the entity-resolution-engineer and dataset-engineer through the coordinator.

WORK ORDER: Phase 5, Subphase 5D implementation and blocked external-prerequisite checkpoint. Starting HEAD is 61d32a38eaad5b2fc352acf0b7f85f3815c2336d on phase-5, and all 5D work is uncommitted.

FILES CREATED: None.

FILES MODIFIED: None. I wrote two temporary hash lists, but only to the session scratchpad and nothing in the repository.

COMMANDS RUN (all read-only inspection):
- Git: git status --short, git rev-parse HEAD, git diff / git diff --stat on the modified ER sources, README and phase reports, git show HEAD:<history files> | shasum, git ls-files -co --exclude-standard, git check-ignore, git log -1.
- File reading: cat, sed -n, grep, jq, wc, ls, du, find, diff on the two retained script copies, shasum -a 256 on the listed key files.
- Freeze check: shasum -a 256 -c over all 556 source-freeze.json entries, plus a file-set comparison against git.
- unzip -p on JDK 17 src.zip, to read the HttpRequestBuilderImpl header-validation message.
- One python3 -I -c inline JSON reader for commands.json. It ran no repository code.
- No builds, tests, sbt, acquisition, provider calls, credential or .env access, or agent launches.

TEST RESULTS:
- I executed no tests. What follows I observed in the retained logs.
- full-check.txt: core 129, Hadoop 64, ER 28, independent 199 and build 4 all succeeded, ending [success] Total time: 411 s … Oct 16, 2026, 10:14:50 PM.
- The injected checkProbeInjectFailure error in that log is expected CheckFailurePathSpec coverage.
- full-check-summary.json matches: 424 tests, 0 failures/errors/skips, 53 reports.


---

BLOCKERS

B1 — Medium — a missing or malformed credential permanently disables the approved pilot
- Where:
  - OpenAIResponses.scala:14-17: the credential is only looked up inside post.
  - LiveAdjudication.scala:184-196: the budget is reserved and saved before dispatch.
  - LiveAdjudication.scala:208-242: any exception becomes TRANSPORT_FAILED and calls ledger.fuse().
  - LiveProvider.scala:282, 311: a fused ledger refuses all further reservations, and no code clears the flag.
  - LiveDemoCommands.scala:71-80: the ledger path is fixed to the approval ID.
- Reasoning: if adjudicate-demo runs without OPENAI_API_KEY, or with a CR/LF or other invalid header character, nothing is ever sent. Even so, one of the 10 attempts is recorded and the approval-scoped ledger is fused permanently. IndependentLiveAdjudicatorSpec:80-89 confirms that a throwing transport fuses the ledger. IndependentLiveCredentialsSpec only tests the transport on its own, not this path.
- Impact: credential availability is a listed remaining gate (runtimeCredentialsChecked: false), so the first live run is exactly where this is likely to surface. It would destroy the user's one-shot $1 approval with zero spend. Recovery would need either a new human approval or editing the ledger, which defeats the budget-continuity design.
- Owner: entity-resolution-engineer.
- Acceptance check: validate that the credential is present and well-formed (full header character set, never logged) before reserving or dispatching. A local credential failure should return a non-fusing, non-reserving trace. Add tests through LiveDemo.run/LiveAdjudicator for missing and malformed credentials (including a non-CR/LF invalid character) that show:
  - zero attempts recorded;
  - the ledger is not fused;
  - no credential text appears in any output;
  - a later valid run can still proceed.
- Blocks handoff: yes, for live-execution readiness. The offline safety properties are unaffected.

B2 — Medium — the 5D demo inputs are labelled as frozen 5C evaluation inputs
- Where:
  - datasets/entity-resolution/prepared/3bfbd651-…retention-manifest.v1.json and 68c2b012-…retention-manifest.v1.json: both have "purpose": "Exact immutable completed preparation input for frozen Phase 5C review population and future human-label evaluation replay."
  - The text is hard-coded at datasets/scripts/retain_prepared_population.py:134.
  - prepared/README.md is unchanged and still describes the directory only as the frozen 5C queue input.
- Impact: both inputs are demo-only. The supplement deliberately contains components overlapping held-out evidence (70 of 93 candidate pairs were excluded). The durable provenance nevertheless calls them evaluat
NONBLOCKING OBSERVATIONS

- N1 (low–medium): code revision and source hash are only format-checked.
  - In LiveDemoCommands.scala:325-329 and LiveDemoExporter:132-135, any 40/64-hex value is accepted and written into the manifest as fact.
  - The previews recorded codeRevision as 61d32a3, a commit that does not contain the 5D code. The coordinator compensated by passing the freeze hash 8396eb78…, which I verified.
  - So "code and source metadata checks" overstates what the code does. Before the live run, either verify these values (HEAD plus freeze) or rename the fields as caller-asserted. Owner: ER.
- N2 (low): possible credential echo when the transport is called directly.
  - The Authorization header is built outside the try (OpenAIResponses.scala:23-29).
  - JDK 17 HttpRequestBuilderImpl:113 throws invalid header value: "%s" with the full value for invalid characters other than CR/LF.
  - In production LiveAdjudicator replaces the message (LiveAdjudication.scala:211) and LiveDemo filters "bearer", so I saw no leak in the CLI path. Fix alongside B1. Owner: ER.
- N3 (low): demo cannotLinks are always empty by construction.
  - They come only from demo decisions, and conflicts are never eligible, so they are always empty (LiveDemo.scala:243-247).
  - Coverage and identifier assertions are complete and checked by the exporter, so conflicts remain derivable. Document that the demo cannotLinks are decision-scoped.
  - Coverage also includes excluded held-out-overlapping supplement endpoints (26 works, 109 researchers). These are source facts with no predictions, which is acceptable.
- N4 (low): stale help text. Phase5Main.scala:15 still says "live adapters and network calls do not exist here" right before the live command help.
- N5 (low): no fsync. The ledger saves via write plus ATOMIC_MOVE without fsync (LiveProvider.scala:252-270), so a power loss could drop the latest reservation.
- N6 (low): traces lost on mid-run failure. An exception during LiveDemo.run after dispatch throws away all traces from attempts already made. Failed attempts are not cached; only the ledger counts survive.
- N7 (info): no backoff on 429. The retry is immediate and ignores Retry-After. At most one retry, so this is harmless.
- N8 (info): report wording. The checkpoint report says it "modified … reviewer prompt", but the prompt was moved to history; I verified the copy is identical. The seed supplement was produced by an earlier script version whose only difference is a weaker validate(). Its executed copy is retained, so the provenance is accurate, but "unchanged dataset validator" is imprecise.

Input-reservation assumption (explicit assessment)

The reservation is wire bytes plus 4,096 tokens per attempt. I judge this an acceptable conservative heuristic for this approval, but not a guarantee:
- Why it over-counts the visible text: a byte-level BPE tokenizer produces at most one token per byte, and JSON-escaping the input string makes the wire body larger than the text the model actually sees.
- What is unverified:
  - that gpt-6-luna's tokenizer is byte-level BPE;
  - how the provider renders the structured-output schema;
  - how large any hidden platform tokens are.
- Why the slack still holds: the worst case is 10 × 69,632 = 696,320 input tokens against 1,000,000 approved. Output is capped exactly by the provider-enforced max_output_tokens (10 × 4,096 = 40,960). Worst-case cost is about $0.11 against $1.00, about 9× headroom. The overrun fuse stops after the first overrun.
- What is not checked: observed totals are never compared against the approved totals, only per-attempt reservations. Given the slack, that is acceptable.

Confirmed by static review (no defect)

- Malformed output can't be accepted: a malformed, refused, incomplete, wrong-model or bad-citation response never produces an acceptance. An "accept" that conflicts with authoritative identifiers falls back to Unresolved.
- Fake and live caches stay separate: live cache keys bind the approval and config, and a cached result is re-validated on read.
- Retries and timeouts are bounded: at most 2 attempts per pair, sequential, with a timeout per attempt.
- Held-out exclusion is sound: pairs touching held-out groups are excluded before scoring. The union-find runs over anchor sets that close over the whole frozen input, so the exclusion is transitive.
- Credentials are not touched when nothing is eligible: with zero eligible pairs, no transport is created and no credential or ledger is accessed.
- Dataset caps were respected: the acquisition request plan is capped at 30 works and 7–14 requests by construction.

---

ASSUMPTIONS:
- I did not independently verify the official OpenAI facts: the alias, the rate card, strict-schema keyword support ($schema, $id, pattern, minItems, minLength, minimum/maximum) and usage field names. official-docs.json notes that the create-reference page returned an Internal Error.
- Test passes come from the retained logs, not from my own runs.

RISKS:
- Compatibility with the real provider is unproven.
- Leakage nobody has observed is still possible, and this is disclosed.
- B1 could cost a human re-approval if it is not fixed before the live run.

MANUAL ACTION REQUIRED:
- User: label the 240 initial reviews (40 development + 200 held-out) with the unchanged blind page and return the original checkpoint files. The 60 reserves are separate.
- Coordinator: route B1 and B2 (and N1/N2 if accepted), then request a fresh review of the repairs.

BLOCKED-ON OWNER: entity-resolution-engineer (B1); dataset-engineer (B2); the user, for the human reviews.

BLOCKED-ON EVIDENCE:
- Real human labels: 0 of 240.
- Naturally eligible non-held-out pairs: 0 in all three sources.
- Actual model calls: 0; spend: $0.00.
- Runtime credential availability has not been checked.

NEXT GATE: owner repairs for B1 and B2, a new freeze, the affected validators and sbt check, then a user-launched re-review. Separately: real-provider evidence and human reviews remain pending. An implementation APPROVE would not satisfy them, and no overall 5D or Phase 5 acceptance, and no 5E advancement, can be inferred from this packet.


Coordinator transcription note: B2 impact ends at “evaluat” in the received message; that truncation is retained. No missing finding wording or acceptance check is invented. The concrete described B2 provenance defect is sufficient for the narrow metadata/purpose repair.


## 5D B1/B2 — repair verification, awaiting external recheck

Coordinator observed successful blocker repairs and fresh verification: 434 sbt tests, 37 Python tests, six validators and an unchanged 557-file freeze. Source delta: 15 modifications, one new test, no removals. Exact reports and original external REQUEST-CHANGES remain retained; no new reviewer verdict exists. B1 recovery does not reset the same approval budget; B2 corrects demo-only provenance without changing data or the accepted 5C manifest. Nonblocking issues were not a separate repair work order. Reviewer prompt is provided only in chat at the user’s request. Actual human reviews, eligible real-model evidence and broader acceptance remain pending; 5E is not authorized.


## 5D B1/B2 recheck — user-supplied external APPROVE

STATUS: COMPLETE (read-only recheck). Verdict for the 5D B1/B2 repair scope: APPROVE.

OWNER: code-reviewer (user-launched, independent).

WORK ORDER: Phase 5, Subphase 5D B1/B2 repair recheck. HEAD is 61d32a38eaad5b2fc352acf0b7f85f3815c2336d; all 5D work remains uncommitted. The authorization is recorded in prompt.md under "5D B1/B2 repair authorization".

FILES CREATED: None. Temporary hash lists went only to the session scratchpad.

FILES MODIFIED: None.

COMMANDS RUN (all read-only inspection):
- Git: git status --short, git rev-parse HEAD, git diff (retention script, its test, READMEs, prompt.md), git show HEAD:<report> compared with diff, git ls-files -co --exclude-standard.
- diff between the current files and the originals preserved in history/5d-initial-review/, for the ER sources, three independent specs, the ER README and both demo retention manifests (via jq -S).
- Reading files: sed, grep, cat, jq, find, stat, comm, wc.
- Hash checks:
  - shasum -a 256 on the listed key artifacts;
  - shasum -a 256 -c over all 557 current freeze entries;
  - shasum -a 256 -c over the 83 evidence/5d/ hashes bound by the preserved original inventory.
- unzip -p on JDK 17 src.zip to read Utils.isValidValue / fieldvchar.
- No builds, tests, Python, provider calls, credentials, .env, acquisition or agent launches.

TEST RESULTS: I ran no tests. These are observed from the retained logs:
- before-fix.txt: the new IndependentLiveCredentialPreflightSpec failed 0/7 against the unrepaired production code. The failure was behavioral: it got "TRANSPORT_FAILED" did not equal "CREDENTIAL_INVALID", not a compile error.
- targeted.txt: 4 owner tests and 40 independent tests passed.
- full-check.txt: core 129, Hadoop 64, ER 29, independent 208 and build 4 all passed, ending [success] Total time: 412 s … Oct 17, 2026, 1:21:56 PM. The nested [error] is the expected injected-failure probe.
- full-check-summary.json: 434 tests, 0 failures/errors/skips, 54 fresh reports, 557 frozen files valid.
- python-tests.txt: 37 tests OK.
- input-integrity-gates.json: 6 validators, all exit 0. The 5C run reports frozen-5c-review; both 5D runs report development-demo.

VALIDATION RESULTS (checked myself):
- All four listed SHA-256 values match. The preserved original freeze hashes to 8396eb78…, the same as the reviewed baseline.
- All 557 current freeze hashes match, and the freeze file set equals git's tracked plus untracked set.
- Comparing the original and current freezes: exactly 15 paths changed, 1 was added (IndependentLiveCredentialPreflightSpec.scala) and none were removed. No retained payload, completion file, run manifest or raw data file is in the delta.
- Retention-manifest hashes match the packet:
  - demo seeds b413bc38…, OpenAlex supplement d9eec30b…;
  - original 5C c5196356…, which is unmodified from HEAD;
  - preserved pre-repair copies 484a3e34… and 7cf7df07…, matching my first review.
- A jq -S diff of each demo manifest shows only purposeKind, purpose and ownership changed.
- All 83 hash-bound evidence/5d/ files are unchanged, and live-state/ still does not exist.
- owner-report.md, test-report.md, repairs.md and review.md remove no lines relative to HEAD.

---

Assessment of the original blockers

B1 — CLOSED. A missing or malformed credential no longer consumes or fuses the approved budget.
- Order of operations. LiveAdjudication.scala:180-203 now goes: render, check the cache, a non-mutating checkReservation, then Try(transport.prepare()), then reserve.
  - A failed prepare, a thrown exception or a null result returns CREDENTIAL_INVALID / LIVE_CREDENTIAL_UNAVAILABLE_OR_INVALID with 0 attempts.
  - It does this before reserve, so the ledger is not saved and not fused.
- Credential handling. OpenAIResponses.scala:15-29:
  - The supplier is read once.
  - It runs the JDK's full header validation via HttpRequest.newBuilder…header(…).build(), which makes no network call.
  - Every failure inside the Try maps to a constant string, so the value-bearing JDK exception message can't escape. This also closes N2: a direct post now throws only the constant.
- No change between validation and dispatch. The prepared transport captures key in a closure, dispatch uses that same value, and retries reuse it (LiveAdjudication.scala:229). Per-pair credential re-reads happen only on later calls to adjudicate.
- Exhausted budget stays lazy. checkReservation runs before prepare, and reserve still re-checks the limits (LiveProvider.scala:273-292). The unchanged test "budget exhaustion refuses dispatch before credential supplier access" passed.
- Disabled, zero-eligible and unapproved paths are unchanged; their tests passed.
- Uncertain post-dispatch failures still charge and fuse (LiveAdjudication.scala transport and termination branches unchanged). IndependentLiveAdjudicatorSpec is unchanged from the original and passed.
- The full enabled LiveDemo path is covered. The wrapper forwards prepare (LiveDemo.scala:311), and the lazy factory is forced inside the adjudicator's Try, so factory exceptions are also contained. IndependentLiveDevelopmentSpec runs missing and NUL credentials through the full path, then recovers on the same persisted ledger.
- Every requested case is tested. IndependentLiveCredentialPreflightSpec covers missing, empty, CRLF, NUL, DEL, non-Latin-1 and supplier-exception credentials. Each asserts a single read, the constant error, 0 attempts, an unchanged durable snapshot, no fuse, no credential text in the trace, and same-ledger recovery to VALIDATED_LIVE.

B2 — CLOSED. The two demo inputs are now truthfully labelled demo-only.
- Both corrected manifests are truthful: "Phase 5D development/demo evidence only; not frozen review, gold labels or held-out evaluation input", with purposeKind: development-demo.
- There is no silent default. retain(…, *, purpose) is keyword-only with no default, and the CLI --purpose is required. check_purpose rejects any manifest without purposeKind unless its runId is the legacy 5C run.
- Inconsistent metadata is rejected. The kind, description and ownership must agree. The known demo run IDs cannot claim the frozen purpose, and the 5C run cannot claim demo.
- Each guarantee is tested: the missing-purpose API/CLI error (exit 2), the inconsistent-purpose rejection, known demo runs claiming frozen, and the legacy 5C manifest hash staying c5196356….
- Payloads are unchanged. b2-metadata-proof.json and my freeze comparison agree.
- Documentation now separates the purposes. prepared/REA embedded space passes preflight and is dispatched. The provider would most likely answer 401, which charges one attempt. It does not fuse and costs nothing, but LiveDemo then continues to the next eligible pair, charging one attempt per pair up to the cap.
  - Impact: possible exhaustion of the attempt allowance with no spend, but only through a provider authentication failure. That is outside B1's "local failure" definition, and no secret is exposed.
  - Owner: ER.
  - Suggested check: restrict the bearer value to the RFC 6750 token charset and/or stop the run after the first 401/403. Add a test that a credential containing U+00A0 records zero attempts.
- O2 (low): a credential-refused run still reports success. adjudicate-demo exits 0 and publishes a complete demo export. Its decisions are Unresolved and carry CREDENTIAL_INVALID, and the summary line shows live attempts=0. The output directory is used up, though the approval is not. Consider a non-zero exit or an explicit refusal message. Owner: ER.
- O3 (info): frozen-5c-review can still be chosen for other runs. A new, unrelated run can be explicitly labelled frozen-5c-review. It is explicit and documented, not silent.
- O4 (info): one original log was never hash-bound. evidence/5d/development-readiness-probe.log (365 bytes, modified Oct 16 21:38, before the first review) is not listed in the preserved original inventory. This predates the repair; no regression.
- Deferred findings. N1 and N3–N8 remain as accepted deferrals, and N2 is closed incidentally by B1.

3. Unverified external prerequisites

- Real human labels: 0 of 240 (40 development + 200 held-out; the 60 reserves are separate).
- Naturally eligible non-held-out pairs for a live demonstration: 0.
- Actual model calls: 0; spend: $0.00. Runtime credential availability has not been checked.
- Compatibility with the real OpenAI API is unverified: strict-schema keyword support, the response envelope and usage fields, and whether the server tolerates whitespace or 0x80–0xFF bytes in the key.
- Passing tests establish neither identity accuracy nor calibration.

---

ASSUMPTIONS:
- The unchanged tests named in the packet passed because they are counted in the full 434-test run.
- I took the original bytes from history/5d-initial-review/, whose freeze hash matches the reviewed baseline. The original LiveDemoExportSpec was not preserved there, so I reviewed its added test as current content.

RISKS: O1/O2 could waste the attempt allowance or confuse an operator during the eventual live run, without spending money. Provider compatibility is untested.

MANUAL ACTION REQUIRED:
- User: complete and export the human reviews from the unchanged blind page.
- Optionally route O1/O2 to the ER owner before any live run.

BLOCKED-ON OWNER: None for this repair scope. The user owns the human reviews; any future, separately authorized step owns obtaining a naturally eligible demo pair.

BLOCKED-ON EVIDENCE: Actual human checkpoints; a naturally eligible non-held-out pair; an observed real-provider run.

NEXT GATE: The human decision on this repaired 5D implementation checkpoint. The 5D exit still requires traceable human reviews and real LLM evidence, or an explicitly accepted blocked checkpoint. This APPROVE does not complete the human-review or real-provider gates, does not establish overall 5D or Phase 5 acceptance, and does not authorize 5E.


Coordinator transcription notes: the received text says “failed 0/7”; the retained before-fix log actually records 0 passed and 7 failed. The received B2 documentation paragraph runs directly into a partial O1 description; this truncation is preserved without inventing missing reviewer text. The explicit APPROVE and closure of B1/B2 are unambiguous. No human acceptance, accepted blocked checkpoint or 5E authorization is inferred from this external verdict. No source changes, tests, model calls or nonblocking repairs were triggered by recording it.


## 5D actual label import and additional bounded search — review boundary

STATUS: No new external verdict exists for the conversion helper, bounded topic-search helper, their tests or resulting new artifacts. The previously user-supplied APPROVE remains limited to the implemented 5D B1/B2 repair scope; it is not widened or rewritten.
OWNER: User selects and launches any independent reviewer; coordinator records this boundary only.
WORK ORDER: User confirmed all twelve batches and authorized import, then explicitly approved the additional bounded search.
FILES CREATED / MODIFIED: Current source-delta.json and review-inventory.json provide the exact inventory. No reviewer prompt file was created or restored.
COMMANDS RUN: Implementation owners and coordinator ran conversion, the unchanged importer, bounded acquisition, metadata-only canonical screens and deterministic tests. No independent reviewer was invoked. ER owner's read-only admission advice is engineering advice, not an external code-review verdict.
TEST RESULTS: See test-report.md and retained execution receipts; test results do not imply review approval.
VALIDATION RESULTS: 240 AI-assisted human-reviewed choices imported; 8 uncertain outcomes preserved; new bounded search added zero admissible observations. No model call or evaluation occurred.
ASSUMPTIONS: User completion confirmation is retained as provenance, not authentication.
RISKS: These are not independent blind gold labels; 22 external-source comments are explicitly AI-attributed and unverified. Provider compatibility remains unobserved.
MANUAL ACTION REQUIRED: Human review of this checkpoint and user-selected external review as appropriate.
BLOCKED-ON OWNER: No implementation owner; human controls further advancement.
BLOCKED-ON EVIDENCE: Naturally eligible non-held-out real-provider evidence; no approval of 5E is inferred.
NEXT GATE: User checkpoint decision. No reviewer launch, commit/push, further acquisition, calibration or 5E.


## 5D label attribution / discovery ordering external findings

User-supplied external B2 finding follows verbatim. No new APPROVE or complete external verdict is inferred from this partial finding. B1 procedural clarification is retained separately in evidence/5d-search-repair/b1-user-clarification.json: already applied at explicit user direction in the reviewing session, with the reviewer/implementer separation departure disclosed. The next reviewer must independently assess both B1 attribution and B2 repair. No reviewer was launched by the coordinator.

```text
B2: The topic-discovery query's sort order guaranteed irrelevant results

Severity: High. Status: open; blocks the bounded-search checkpoint.

Where: datasets/scripts/acquire_screened_demo.py:78-80. discovery_url() sends search=<topic> together with sort=publication_date:asc.

Evidence:
- The retained datasets/entity-resolution/5d-demo-2026-10-20-screened/responses/001-openalex.body and 002-openalex.body show OpenAlex reading the query as "with (…) in the full text, oldest first".
- The two searches matched 323,411 and 467,092 works.
- The first five results of each are unrelated 2018 repository records:
  - "Neocosmicism: God and the Void"
  - a New England groundwater-quality report
  - "Spanish Orientalism: Washington Irving and the Romance of the Moors"
  - "The Automotive Supply Chain: Global Trends and Asian Perspectives"
- Sorting by date ascending throws away relevance ranking, so the CS venue filter rejecting all 10 records was close to inevitable.
- datasets/scripts/test_screened_demo.py has no check of the discovery query's search or sort behavior, so the tests couldn't catch this.

Impact:
- The recorded result ("10 returned, all excluded by the CS venue filter, zero admissible, no author seeds") is real, but the query design caused it. It does not show that no eligible CS evidence exists.
- These reports describe the result without saying why it happened:
  - docs/agent-runs/phase-05/evidence/5d-followup-demo/outcome.json
  - the 2026-10-20 follow-up section of datasets/entity-resolution/README.md
  - docs/agent-runs/phase-05/owner-report.md:545-563
- The one approved search was used up on off-topic results, with only 2 of 20 attempts and 10 of 30 records. That weakens the "blocked on naturally eligible evidence" conclusion for the $1 live demo.

Required owners:
- dataset-engineer:
  - Fix discovery_url() by removing the date sort or using relevance ordering. Consider title_and_abstract.search instead of full-text search.
  - Add an offline test that asserts the discovery URL's search and sort behavior.
- coordinator: add an append-only root-cause note to the follow-up evidence, the dataset README section and the owner report.
- human: decide whether to authorize a re-run of the corrected search. The recorded strategy forbids refill or re-run, so it needs a new explicit approval with stated limits.

Acceptance checks:
- [ ] The cause is disclosed in evidence/5d-followup-demo/, the dataset README and the owner report. Existing records are not rewritten.
- [ ] The fix and its new test pass offline: python3 -m unittest discover -s datasets/scripts -p 'test_*.py'.
- [ ] No new HTTP request is sent without a recorded user approval.
- [ ] If a re-run happens, it gets a new separate stage manifest. Cumulative counters must not be reset, and canonical held-out exclusion must still run before any scoring.

Next gate:
1. Fix and test.
2. Record your re-run decision.
3. Refresh the source freeze.
4. Run sbt -batch check, the Python tests and the 7 integrity validators.
5. Run a fresh independent recheck. That recheck also confirms the B1 attribution record.
```


### B1 clarification and B2 implemented repair — external verdict pending

The user confirmed that B1 implementation was already applied at their explicit direction in the reviewing session; the departure from reviewer/implementer separation is disclosed in b1-user-clarification.json. The coordinator preserved that label tree unchanged and included it in the new freeze. B2 has been implemented and exercised with a newly approved, separately manifested rerun. The original flawed run remains intact and is explicitly qualified by append-only root-cause notes.

The source-level repair and passing tests do not constitute independent approval. The next user-selected reviewer must assess both B1 attribution and B2 query/history/evidence behavior. No new external verdict is inferred, no reviewer was launched, and the overall 5D real-provider exit remains unfulfilled. Current eligibility result is local to the measured population; it is not an exhaustion claim about CS evidence.


## User-supplied independent B1/B2 recheck APPROVE

The user returned the complete independent read-only recheck with the verdict: “STATUS: COMPLETE. Verdict for the implemented B1/B2 scope is APPROVE: no blockers, four nonblocking findings, and the gates I could not verify are listed below.” The reviewer states they did not author B1 or B2, verified the attribution, all 742 source hashes, counters/history, retention and retained gate evidence, and explicitly did not approve overall 5D or authorize 5E. A bounded summary is retained in evidence/5d-focused-demo/prior-external-approval-summary.json; it is labelled a summary rather than a verbatim full transcript.

N1 (literal line-number prefixes in earlier B1 phase sections), N2 (historical copied-source date/snapshot relabelling), N3 (some asserted rather than measured proof fields), and N4 informational observations remain deferred. No historical report, decision or source artifact is rewritten to fix them. The next focused search is a new user-authorized work item, not an inferred permission from this review. No reviewer has been launched by the coordinator.


## Focused-search implementation review boundary

The prior user-supplied independent APPROVE covers B1/B2, not the newly authorized focused acquisition and offline CS slice. These new helpers/tests and their outputs have implementation-owner tests and coordinator gates; no independent verdict for them is inferred. The five raw repository false positives were disclosed and excluded through a separately manifested immutable-parent slice before ER. The user alone selects and launches any new reviewer. No reviewer prompt file was created or restored. No reviewer was launched by the coordinator. Overall 5D provider evidence remains pending; this checkpoint does not authorize 5E.


## 5E limited deterministic/fake evaluation — observed handoff

External verdict: PENDING. Coordinator engineering/test evidence is not independent approval. See evidence/5e/evaluation-report.md. User authorized limited offline evaluation with real-provider requirement still open; no overall Phase 5 acceptance or Phase 6 authorization is inferred.


## Final targeted real-provider attempt after limited 5E review

The user returned an independent APPROVE for limited 5E and the implemented changes (zero blockers, six nonblocking observations), explicitly leaving real-provider evidence and overall acceptance open. The user instructed that nonblocking findings need no repair. The user then replied “alright do it” to one final targeted attempt with unchanged rules and existing $1 budget. This does not authorize Phase 6, commit/push, changes to labels, policy or approved evaluation. Preparation starts offline; new public acquisition waits for explicit numerical limits. Summary-only review receipt: evidence/5d-final-attempt/prior-review-summary.json; start/protected snapshot: start.json.


## Final Rice-team bounded attempt — verified blocked provider checkpoint

External verdict for this new dataset/evidence checkpoint: PENDING. Earlier limited5E APPROVE remains scoped to its reviewed state. No new reviewer was launched or acceptance inferred. See evidence/5d-final-attempt/report.md.


## Versioned adjudication request eligibility revision — awaiting external review

STATUS: PENDING USER-LAUNCHED INDEPENDENT REVIEW. No reviewer was triggered and no approval is inferred. See evidence/5d-eligibility-revision/report.md and outcome.json. Prior review verdicts remain unchanged.


## Safe response diagnostics repair — external review pending

No independent reviewer was launched. Implementation evidence: evidence/5d-response-repair/report.md. Earlier two real responses failed validation; no successful adjudication or full acceptance is inferred.


## Eligibility revision, diagnostics and observed live response — review pending

STATUS: PENDING USER-LAUNCHED INDEPENDENT REVIEW. The latest retained run contains one VALIDATED_LIVE response, cumulative four attempts and $0.005576 cost upper bound. System outcome remains UNRESOLVED with zero links. No reviewer was invoked and no approval or human acceptance is inferred. See evidence/5d-response-repair/provider-success-report.md and provider-success-proof.json. Earlier verdicts and all failures remain retained.


## User-supplied external checkpoint APPROVE and subsequent human acceptance

The user returned an independent read-only APPROVE for the eligibility revision, response diagnostics and observed live adjudication checkpoint: zero blockers and five nonblocking observations. Complete supplied report: [external-review.md](evidence/phase5-human-acceptance/external-review.md). N-1 ledger durability, N-2 eligibility-count/evaluation interpretation, N-3 selection disclosure, N-4 reject-or-advisory asymmetry and N-5 validation-rate reporting remain deferred under the user's instruction to ignore nonblocking bugs. The review's stated unverified gates and broader limitations are retained without converting them into independently executed checks.

After the coordinator explicitly identified human acceptance of Phase 5 with the documented limitations as the next step, the user replied “I approve them”. That separate human decision is transcribed append-only in human-gate.md and bound in evidence/phase5-human-acceptance/human-acceptance.json. Reviewer approval and human acceptance are separate records. No reviewer was launched by the coordinator; no nonblocking repair, commit, push or Phase 6 work follows from this recording.

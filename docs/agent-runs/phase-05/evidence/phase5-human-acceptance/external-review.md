Phase 5 checkpoint review: eligibility revision, response diagnostics and observed live adjudication

VERDICT: APPROVE for this checkpoint only. There are no blockers. I found five nonblocking observations, listed below.

This verdict does not record human Phase 5 acceptance. It does not authorize a commit, a push or Phase 6.

---

STATUS: COMPLETE (read-only review)

OWNER: code-reviewer. This is an independent review launched by the user.

WORK ORDER: The user's pasted review prompt for the eligibility revision, response diagnostics and observed live checkpoint. HEAD is 6285210f; the whole-phase base is 099e3033.

FILES CREATED: None

FILES MODIFIED: None

COMMANDS RUN: All read-only.
- git rev-parse, git status, git diff and git ls-files.
- sed, cat and grep over source, tests, README and evidence.
- shasum -a 256 on the five key files.
- Python with -I for hashing and JSON/XML inspection:
  - recomputed all frozen source hashes;
  - recomputed the review-inventory hashes;
  - checked the hashes referenced by the review packet;
  - re-read all 60 retained JUnit XML reports;
  - resolved the successful response's cited JSON pointers against the request evidence;
  - followed the budget chain across all five live runs.
- WebFetch of the course README's Phase 5 section.

I did not build, test, call a provider or open .env or any credential file. One read-only command was blocked by the project's guard hook because it mentioned a .claude/ path. I re-ran it without that path.

TEST RESULTS: I ran no tests. These are retained results, which I checked against the files on disk:
- Retained full gate: 469 tests, 0 failures, errors or skips (core 129, Hadoop 64, ER 39, independent 233, build 4).
- JUnit reports: all 60 XML files exist, and their timestamps are unchanged since the gate. Their counts add up to 469.
- New suites: RequestEligibilitySpec 5, ProviderResponseDiagnosticSpec 4, IndependentRequestEligibilitySpec 14, IndependentLiveResponseDiagnosticSpec 5.
- Not re-executed at this checkpoint: the 97 Python tests and 14 integrity validators. They are retained from the eligibility stage, as the reports say.

VALIDATION RESULTS: These are my own hash checks.
- Key file hashes: all five SHA-256 values in the prompt match.
- Frozen sources: all 965 match source-freeze.json. No in-scope tracked or untracked source file is missing from the freeze.
- Review inventory: all 254 files listed in review-inventory.json match.
- Review packet: every path it references matches its stated bytes and SHA-256. The three live-run manifest hashes in provider-success-proof.json also match.
- Not rechecked: the 1,117 protected-file proof and the 1,019 runtime class/resource hashes. I took both from retained evidence.

What I confirmed by reading code and evidence:

1. Eligibility versus acceptance
   - RequestEligibilityPolicy.eligible (lines 105–118) still requires an UNRESOLVED pair inside the inclusive band.
   - The extra request route applies only to Researcher pairs. It requires all of: name ≥ 0.8, initials = 1.0, comparable affiliation ≥ 0.8, and coauthor overlap > 0. Coauthor overlap is undefined for same-publication pairs (FeatureExtractor.scala:204).
   - Model acceptance is gated on initial.sufficient and on the absence of a conflict, both in ResolutionEngine.scala:310 and in LiveDemo.
   - Conflicts and exact-ID pairs never reach the request path, because their outcome is not Unresolved.
   - This matches the course rule: "LLM adjudication only for a bounded unresolved band."
2. Strict response validation
   - The validateResponse code is unchanged. safeResponseFailureCode covers all 18 of its require messages, and anything unknown maps to SCHEMA_OR_FORMAT.
   - The diagnostic keeps only:
     - byte counts and SHA-256 hashes;
     - a fixed set of 7 identity booleans;
     - an outcome from an allowlist;
     - counts.
   - Diagnostics are attached only to non-retried content failures, and they are wrapped in Try, so a charged trace is never lost.
3. Bindings and legacy compatibility
   - The bound policyVersion embeds the profile's full fingerprint.
   - validateBinding refuses all of these: a missing profile, a mismatched profile, an unbound policy and double binding. This holds in the engine, the selection code, both exporters and the offline verifier.
   - The legacy fingerprint ad8c520f… is asserted by tests.
   - The live request, cache key and exports all carry policyHash da0fe66a….
4. Held-out exclusion
   - All three live runs bind the same frozen/queue/split hashes.
   - They admit the same 11 supplement pairs and exclude none.
   - The successful pair is one of the admitted supplement pairs, not a held-out pair.
5. Budget continuity across runs

| Run           | Attempts after run | Cost upper bound | Result                               |
|---------------|--------------------|------------------|--------------------------------------|
| live, 192650Z | 0                  | $0               | Credential failure; consumed nothing |
| 193340Z       | 2                  | $0.002772        | Two content rejections               |
| 195406Z       | 3                  | $0.004196        | FIELD_NOT_FOUND                      |
| 201707Z       | 4                  | $0.005576        | VALIDATED_LIVE                       |
   - The config hash fea364d4… and approval ID are the same throughout. The budget never fused or reset.
6. The successful response
   - Its six echoed identity fields match the request.
   - I resolved all four cited pointers myself. The two nameText pointers read "Christopher Jermaine" and the two observedOpenAlexAuthorId pointers read A5109437922.
   - cacheHit is false.
   - The final decision is UNRESOLVED (score 0.6933) with LLM_ACCEPT_BLOCKED_INSUFFICIENT_ACCEPTANCE_EVIDENCE, and accepted-links.jsonl is 0 bytes.
7. Revised evaluation
   - The re-run on the previously exposed held-out set is bound to the revised policy.
   - It is explicitly labeled descriptive.
   - Its metrics are identical to the original's.

Findings. None of these blocks this checkpoint.

- N-1. The budget ledger can silently reset if its file is lost. Severity: Medium-Low.
  - Path: modules/entity-resolution/src/main/scala/edu/uic/cs441/scholarchain/entityresolution/LiveProvider.scala:243-268 (if (Files.exists(path)) … } else empty), and the untracked file docs/agent-runs/phase-05/evidence/5d/live-state/approval-1b66c9878075/budget.json.
  - Evidence: A missing ledger is treated as a fresh zero state. That file now records 4 charged attempts and is untracked (??). The committed 5d/live-runtime-binding.json points to it.
  - Impact: If the evidence tree is cleaned or not committed, a later adjudicate-demo under the same approval would start at 0 attempts. That would allow 10 more attempts instead of the 6 that remain under the $1/10-attempt approval. The current claim that the budget was "not reset" relies on keeping this file. This is related to the deferred N5 (no fsync) but is a different issue, and it matters more now that real charges are recorded.
  - Owner: The coordinator must retain the ledger and cache with the evidence; the human decides whether to commit. Optionally, the ER owner adds a guard against re-initializing a ledger for an approval that has recorded usage.
  - Acceptance check: The ledger is kept in any accepted commit, or the human records the approval as closed. For an optional code guard, add a test that a missing ledger for a previously used approval is refused.
- N-2. The revised evaluation is a no-regression check by construction, and newly eligible pairs are not reported. Severity: Low.
  - Path: docs/agent-runs/phase-05/evidence/5d-eligibility-revision/post-policy-evaluation/comparison-with-original.json:3; compare fake-a-resolution-manifest.json (fakeCalls 10) with evidence/5e/fake-a-resolution-manifest.json (fakeCalls 0).
  - Evidence: In disabled and fake modes the model either does not run or always abstains, so outcomes cannot change. The revision made 10 frozen-population pairs newly request-eligible. Neither the comparison nor the report gives that count or how the pairs split across development, held-out and unlabeled.
  - Impact: A reader might take "metrics unchanged" as evidence about the revised LLM path. It says nothing about that path.
  - Owner: coordinator, with the ER evaluator owner.
  - Acceptance check: Add the newly eligible count by partition, computed without reading labels. State that unchanged metrics are expected because of how disabled and fake modes behave.
- N-3. The README and reports understate how the eligibility rule was chosen. Severity: Low.
  - Path: modules/entity-resolution/README.md:808 compared with evidence/5d-eligibility-revision/design.md:11.
  - Evidence: The README says the values were chosen "before inspecting the real candidate outcome." design.md also discloses that the coordinator already knew the aggregate Rice feature summary. The rule was adopted after the final acquisition found zero naturally eligible pairs, and the live pair is a Rice supplement pair.
  - Impact: The live pair is not representative of naturally eligible traffic. Plan §9 warns against manufacturing a demo. No scores were changed and the user explicitly authorized the revision, so this is a disclosure gap, not a violation.
  - Owner: ER owner for the README; coordinator for the reports.
  - Acceptance check: Bring the README and the provider-success report in line with the design.md disclosure.
- N-4. The model's accept can never take effect on request-only pairs. Severity: Low (interpretation).
  - Path: RequestEligibilityPolicy.scala:118, ResolutionEngine.scala:310-313 and the effective researcher policy (requiredGroups [name, context], 3 groups).
  - Evidence:
    - The request-only route adds exactly the pairs that lack sufficiency, so a model "accept" on them is always blocked.
    - A model "reject" still produces REJECTED. It creates no cannot-link constraint, because cannot-links come only from conflicts (ResolutionEngine.scala:411).
  - Impact: Through this route the LLM can only reject or advise. The one validated "accept" changed no decision. This is the intended, conservative behavior, but the asymmetry should be stated plainly.
  - Owner: coordinator / documentation.
  - Acceptance check: One sentence in the provider report stating this reject-or-advisory asymmetry.
- N-5. The validation-failure rate is not reported. Severity: Info.
  - Path: evidence/5d-response-repair/provider-success-report.md:10.
  - Evidence:
    - The same request (requestHash 6d8ee9ec…, unchanged prompt, schema and settings) was sent in three separate invocations.
    - Only 1 of the 4 total attempts validated, and only 1 of the 3 sends of this request.
    - The sequence is described, but plan §9 Stage B asks for failure and abstention rates, and no rate is given.
    - Re-sending until a response passes validation is harmless here because the outcome was blocked anyway.
  - Owner: coordinator.
  - Acceptance check: State the per-attempt validation rate in the provider report and the outcome file.

ASSUMPTIONS:
- The provider IDs, usage figures and timestamps are as recorded. They cannot be independently authenticated.
- human-gate.md was created at the user's request before this stage, as the record states.
- The course text matches the WebFetch summary, which covered only the first 100k characters of the README.

RISKS:
- The request rule is uncalibrated.
- The single response relies on a shared OpenAlex author hypothesis, which is not independent identity verification.
- The model's confidence of 0.99 is uncalibrated.
- Ledger durability (N-1).
- Pair selection could be biased (N-3).

MANUAL ACTION REQUIRED:
- human-gate.md is human-owned and is now out of date: it still says provider attempts are 0 and the requirement is unsatisfied. Only the human may record a new decision about the provider requirement and overall Phase 5 acceptance.
- The human should decide how the live-state ledger and cache are retained before any commit.

BLOCKED-ON OWNER: None

BLOCKED-ON EVIDENCE: None for this checkpoint. These gates remain unverified:
- the 1,117-file protected proof and the 1,019 runtime-hash proof, which I did not recompute;
- the Python and integrity validators, which were not rerun at this stage;
- provider authenticity beyond the recorded identifiers.

NEXT GATE: The human decides on overall Phase 5 acceptance. If wanted, the five observations go to their owners; the user previously said nonblocking issues need not be fixed. No commit, push or Phase 6 is authorized by this review.

---

Broader Phase 5 limitations, unchanged by this review

- Labels were reviewed by a human with AI assistance; they are not blind gold.
- Eight initial reviews remain uncertain, leaving 38 development and 194 held-out binary labels.
- The external evidence behind 22 assisted cases was not retained.
- Real-provider integration evidence now exists. LLM-path accuracy, calibration, blocking recall and global identity recall remain unmeasured.
- Instructor acceptance of the Codex/Cursor workflow deviation is not inferred.

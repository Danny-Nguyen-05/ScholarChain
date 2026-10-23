# Phase 7 work order — Subphase 7A only

User request (verbatim):

> '/Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase7.md' 
> You are the Phase 7
> coordinator for /Users/danny/Documents/UIC/CS441/ScholarChain. Execute
> Subphase 7A ONLY. Begin with Step 0: first read
> docs/agent-runs/phase-06/human-gate.md and repairs.md, then ask me all your
> questions (7-1, 7-2, 7-3 and the Section 7.6 carry-over items) with
> recommended defaults, and wait for my answers before editing anything. Use
> the JDK 17 environment from Section 2 for every sbt command. Do not trigger
> any code reviewer. When 7A is done or blocked, return the handoff packet and
> the filled-in reviewer prompt from Section 10 in one copyable code block,
> then STOP and end your turn. Do not start 7B.
> DO you have any questions before we start

Step 0 response (verbatim): **Accept all recomended defaults**.

The supplied plan has sections 7.1–7.5 and no Section 7.6. Coordinator disclosed this and asked about the Phase 6 repairs carry-forward register instead. User accepted all ten recommended defaults before any edits or agent launches:

1. 7-1: Main-code fakes in modules/storage, reusable downstream.
2. 7-2: No Docker dependency; in-memory fakes and SDK request-shape stubs.
3. 7-3: Include ResearcherMetricCache keyed by researcherId/windowId with metric version/run provenance.
4. Preserve Spark IDs and source works; omit unknown collaboration years, never fabricate dates. Frozen domain contracts unchanged; additive core work only through domain owner if blocked.
5. Collision-safe support key edgeId+workId; concrete DynamoDB keys and conditional run-state transitions; historical manifests/IDs unchanged.
6. Validate kcore/collaboration equivalence, store one canonical copy, reject conflicting duplicates.
7. Preserve Converged: false, iteration limits and approximate-P90 qualifications; no upstream algorithm repairs.
8. Other Phase 6 findings remain routed/deferred to original owners/gates. Summary improvements before Phase 8; historical evidence retained.
9. If current AWS docs rule out Parquet, assign a small neptune-opencypher-csv export to spark-engineer within 7A, exact IDs, tests, existing tables/formulas unchanged.
10. Create phase-7 from current clean phase-6 HEAD.

The plan snapshot is evidence/7a/phase7-plan.md; original path/hash and initial git state are in evidence/7a/preflight.json. This record captures work-order answers, not human acceptance or constitutional ratification. Specialist work is delegated using native Codex agents; none may spawn another agent. No reviewer, cloud mutation, paid provider call, commit or push is authorized. 7B is not started.


## Subphase 7A repair round 1

User supplied the external REQUEST-CHANGES review retained verbatim in review.md and evidence/7a/repair-1/external-review.txt, then instructed: **Fix all blocking bug for me.** This repair is F1/F2 only. N1–N8 remain open/nonblocking. No questions for this repair round. Existing uncommitted reviewed7A changes remain in place on phase-7; proceeding is explicit in this repair work order. No7B, reviewer, commit/push, cloud/provider calls or prior human-record edits.

F1 owner storage-engineer repairs strict producer decimal-string count parsing and module tests; test-engineer corrects the independent fixture and regression. Producer output, IDs and hashes remain unchanged. Optional read-only retained-export smoke authorized.
F2 coordinator renames all retained7A .log evidence to Git-visible .txt, updates authored path references, verifies old/new SHA256 bytes and git visibility, preserving original review text and raw /tmp command history. .gitignore remains unchanged. New evidence is retained under evidence/7a/repair-1/ using .txt.

Run affected storage/IndependentStorage*/NeptuneCSV targets, then fresh fullcheck with exact Section2JDK17 environment. Record java-version, exact commands/exits/groupcounts/rawhashes. Return Section10 handoff plus filled repair-round1 recheck prompt in one code block, then stop. No next subphase.

### User-supplied repair work order (verbatim)

You are the Phase 7 coordinator for /Users/danny/Documents/UIC/CS441/ScholarChain,
working from /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase7.md
(accepted snapshot docs/agent-runs/phase-07/evidence/7a/phase7-plan.md,
SHA256 b54aa12309007bf4758120d8297d1de2eccb497220d3f0de87dc5563fef74ebb).
This is Subphase 7A REPAIR ROUND 1. Do NOT start 7B.

1. Append the external reviewer's verdict below VERBATIM to
   docs/agent-runs/phase-07/review.md under "Subphase 7A", marked
   "user-supplied external review (repair round 1 input)". Log findings F1, F2
   (blocking) and N1–N8 (nonblocking, listed but not required) with owners
   in docs/agent-runs/phase-07/repairs.md. Do not rewrite earlier records.

2. Fix ONLY the blocking findings, each through its named owner:
   - F1 → storage-engineer (modules/storage/**) and test-engineer (tests/**).
     LocalParquetManifestReader (ManifestRows.scala:75) must accept the
     producer's run-metadata rowCount encoding: a JSON string of exact
     decimal digits, as written by Phase6Export.scala:321 (ujson Long → Str).
     Reject malformed counts. Do not change Phase 6 output, IDs or hashes.
     Module tests (ParquetManifestSpec) and the independent fixture
     (IndependentStorageParquetSpec) must use the producer's string
     encoding, and a new test must cover the string form. Optional and
     owner's choice: a local read-only smoke opening one manifest from the
     retained export target/phase6-runs/6fg-spark-first-v2/run:f02acf56-...
     (no writes to that directory, no cloud).
   - F2 → coordinator. Retain every docs/agent-runs/phase-07/evidence/7a/**/*.log
     as a tracked .txt (Phase 6 precedent). Update every path reference in
     build/log-index.json, targeted-*.json and spark-targeted-*.json, and in
     the reports. Re-verify the recorded SHA-256 values. Do not edit
     .gitignore (build-engineer owns it).
   Ask Step 0 questions first if anything is ambiguous; otherwise say
   "No questions for this repair round" and proceed.

3. Rerun the affected targets (storage tests, IndependentStorage*Spec,
   Phase7NeptuneExportSpec), then a fresh full check, using the plan's
   Section 2 JDK 17 environment exactly:
     export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
     export PATH="$JAVA_HOME/bin:$PATH"
     export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
     sbt -batch check
   Report java -version, exact exits, per-group test counts and raw log hashes.
   Retain evidence under evidence/7a/repair-1/ as tracked files.

4. Do NOT launch any reviewer. Do not commit or push. No cloud or provider calls.

5. Return the Section 10 handoff packet and a filled-in RECHECK reviewer
   prompt (Subphase 7A repair round 1) in one fenced code block, listing
   prior findings F1/F2 with their repair evidence and N1–N8 as open
   nonblocking items. Then end with: "Subphase 7A repair round 1 is ready for
   review. I have stopped and will not start the next subphase until I
   receive the next prompt." and STOP.

User action request: Fix all blocking bug for me.


## Subphase 7B — user work order and Step 0

# Subphase 7B work order

User: “alright let implement phase 7b”

Step 0 answers: “accept all recommended defaults”

- N1: Store source-run qualifications once, referenced by run ID and SHA-256 from each metric item, preserving all qualifications.
- N2: Verify CSV sidecar hashes in loader and run bounded local replay from retained real data into new temporary output; original export untouched.
- N3: Use fixed ClientRequestToken per logical DynamoDB transaction.
- N4-N9: Defer nonblocking items; N6 remains 7C.
- existing: Fakes/SDK stubs; no Docker dependency; no AWS/provider calls; no reviewer; only 7B; no stage/commit/push.

Implement only plan Section 8 Subphase 7B using the accepted snapshot. Native storage/test owners, and scoped Spark bounded replay only. No reviewer, cloud/provider calls, staging, commit or push; stop before 7C. Exact JDK 17 environment required for every sbt command. Evidence uses Git-visible files, no *.log.

Base: 08e3d21233dbaf8c3d6283fc3bb9bce7f7fb1276 on phase-7. The approved 7A implementation/review/evidence is committed and working tree was clean before this evidence.


## Subphase 7B repair round 1 — user work order

The complete user-supplied external review and next prompt are retained verbatim in evidence/7b/repair-1/external-review.txt and appended to review.md. User instruction: “Fix all blocking bugs for me”. Only F3/F4 repairs are authorized; the uncommitted 7B tree remains in place. No questions for this repair round. No reviewer, AWS/provider calls, stage/commit/push, human record edit or 7C work.


## Subphase 7C — work order and accepted Step 0

User: “alright let do phase 7c now”. Step0 response: “accept all recommended defauls”. Approved7B commit confirmed on phase-7 at c911b236f2a8c02b7422df56f8c334d47fff7ad3; clean working tree before delegation.

- independent: Plan7C hardening. Runtime roots rag/services plus storage composition used by them; currently empty runtime modules disclosed, scanner has regression fixtures.
- N6: Include S3 existing-key412 and Dynamo ledgerCAS/transactioncancel SDK stubs, test-engineer.
- deferred: N4,N5,N7,N9–N16 deferred and documented; N8 process note retained.
- liveSuite: Author and compile only, never execute here. Exact tag and SCHOLARCHAIN_AWS_ITEST=1, explicit AWS_PROFILE, config path SCHOLARCHAIN_AWS_ITEST_CONFIG.
- cleanup: Terraform-provisioned resources only; unique fixture IDs/keys; delete only suite-created data in future authorized execution; no bucket/table/index resource creation/deletion.
- budget: Document5USD incrementaltestbudget excludingexistinginfrastructure; Phase14Ccurrentpricing/budgetvalidationrequired, no hardbillingguarantee.
- buildReadme: No build change unless compilation requires it; complete required README schemas/keys/indexes/metadata/batches/retries/idempotency/citations/cleanup.

Only plan Section8 Subphase7C; exact JDK17 for every sbt command. Live suite authored and compiled, never run. No reviewer, AWS/provider calls, staging, commit/push, human record edits or Phase8.


## Subphase7C repair round1 — user-requested7C-M1

User supplied external APPROVE with nonblocking findings, then requested: “Fix the first medium bug for me”. Only7C-M1 is authorized: counted Neptune deletes and reader point-absence checks before journalcleaned, plus offline zero-match regression. Other findings remain deferred. No questions for this repair round. Existing7Cuncommittedtree retained; no live suite/provider/AWS/cleanup/reviewer/stagecommitpush/humanrecord/Phase8. Full original review output retained repair-1/external-review.txt and appended verbatim to review.md.

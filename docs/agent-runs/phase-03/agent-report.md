<!-- Course-named copy of owner-report.md in this folder, added in Phase 17 (package 17D, docs/agent-runs/phase-17/prompt.md). The text below this note is identical to owner-report.md, which is unchanged. -->

# Phase 3 owner reports

STATUS: COMPLETE for the sixth-review repairs. Not a Phase 3 acceptance.

OWNER: `dataset-engineer` and `domain-engineer`, assembled by the coordinator. `.gitignore` bytecode rules were edited by `build-engineer` `c20c18fb-0588-4471-8543-019cf171e2f9`.

## Dataset-engineer

Latest agent: `a2ab7fcc-f51e-46e9-9069-b6173ec85778` (`composer-2.5-fast`).

Portfolio remains DBLP, OpenAlex, ORCID, and Crossref. Sixth-review repairs: API responses are capped at 512 KiB; the DBLP sample DOCTYPE is an internal subset `<!DOCTYPE dblp []>` with no external DTD; `datasets/schemas/orcid-record.md` now records the DOI in `activities-summary.works.group[7]`. October 2026 DBLP provenance remains in `datasets/provenance/dblp-snapshot-2026-10-03-dagstuhl.txt`.

Owner-reported commands, all exit 0: `acquire_samples.py --mode regenerate`, `validate_datasets.py`, `shasum -a 256 -c samples/SHA256SUMS`, and `test_acquire_bounds.py` (6 tests).

## Domain-engineer

Latest agent: `4ca492d9-7777-4970-a10f-1a75ba15b238` (`composer-2.5-fast`).

Sixth-review repairs under `modules/core/**`: coauthor average and maximum set to 1 for the one-publication fixture and rejected when inconsistent; duplicate team mentions rejected; pair work IDs bound to the source observation rather than a jointly rewritten DOI; graph-path evidence requires `graphPath`; metric and edge evidence carry locator fields; graph edges reject malformed endpoints and non-numeric counts; Crossref `sourceRecordId` must match the work DOI; graph years must be in 1..9999; versioned file `modules/core/src/main/resources/scholarchain.config.v1.json` loads through `ConfigLoader`.

Owner-reported `sbt -batch check`: exit 0, 52 core tests succeeded, 2 build-verification tests succeeded.

## Coordinator-observed checks

Run by the coordinator on 2026-10-05 after both owners finished, from `/Users/danny/Documents/UIC/CS441/ScholarChain`, Homebrew Java 17.0.20.1, sbt 1.10.7:

- `python3 -B datasets/scripts/acquire_samples.py --mode regenerate` exit 0. Output: `verified 4 committed sample(s) against SHA256SUMS`.
- `/tmp/scholarchain-datasets-venv/bin/python -B datasets/scripts/validate_datasets.py` exit 0. Output: `OK: manifest (4 datasets), samples, and script bounds validated`.
- `python3 -B datasets/scripts/test_acquire_bounds.py` exit 0. `Ran 6 tests` `OK`.
- `cd datasets && shasum -a 256 -c samples/SHA256SUMS` exit 0. All four samples `OK`.
- `sbt -batch check` exit 0 at 5:18:22 PM. Core `Total number of tests run: 52`, `succeeded 52`. Build-verification `Total number of tests run: 2`, `succeeded 2`. The nested probe logged `scholarchain check probe: injected format-stage failure` and `CheckFailurePathSpec` passed. Final line: `[success] Total time: 13 s`.

ASSUMPTIONS: JSON remains the configuration profile. No YAML or HOCON library was added.

RISKS: The new evidence locator fields and pair DOI binding are contract changes. API refresh caps reject oversized bodies but do not prove the live APIs stay small. The DBLP sample is self-contained for ElementTree; it is not a full upstream DTD validation.

MANUAL ACTION REQUIRED: Independent read-only review, then human acceptance. No commit or push was performed.

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: none

NEXT GATE: `code-reviewer` on `inherit`. This report does not accept Phase 3.

## Delegated domain repair after eighth review

STATUS: COMPLETE for implementation and owner-run gates; independent review and human acceptance pending.

OWNER: `/root/phase3_domain_repairs`, `domain-engineer`. The coordinator assembled this owner report. The agent edited only `modules/core/**` and made no commit or push.

WORK ORDER: All eight eighth-review findings and the independent acceptance checklist recorded in `prompt.md` and `repairs.md`.

FILES CREATED:

- `modules/core/README.md`
- `modules/core/src/main/scala/edu/uic/cs441/scholarchain/core/WorkValidationContext.scala`
- `modules/core/src/main/resources/scholarchain.config.v1.conf`
- `modules/core/src/test/scala/edu/uic/cs441/scholarchain/core/ContractRepairSpec.scala`
- `modules/core/src/test/resources/wire/graph-edge-orcid-employment.json`

FILES MODIFIED:

- Core main sources `ConfigLoader.scala`, `DomainValidation.scala`, `Records.scala`, `StableIds.scala`, and `Violations.scala`.
- Core test sources `ConfigLoaderSpec.scala`, `Fixtures.scala`, `SerializationContractSpec.scala`, and `ValidationSpec.scala`.
- `modules/core/src/test/resources/wire/graph-edge.json`.

VALIDATION RESULTS / CONTRACT CHOICES:

1. Removed the global bibliography registry and URI fallback. Full pair/authorship/team checks require an explicit validated work or immutable context. Single-argument checks return `MissingValidationContext`; `checkStructure` is explicitly structural.
2. Context identity is source, source record, and dataset snapshot. Identical duplicates are accepted; conflicting observations, including lineage differences for the same key, return deterministic errors. A later derived run may reference the acquisition snapshot.
3. Direct DOI/arXiv resolver links, including nested author provenance, must agree with work identifiers. Unrelated URLs do not supply bibliographic authority. Crossref source-record DOI remains authoritative when its optional DOI field is absent.
4. Bound records must match actual work mention membership, pair bibliography/year, authorship position, and complete ordered teams. Researcher identity decisions remain later-phase work.
5. Metrics explicitly describe a complete deduplicated canonical graph/publication population in the same policy/window. Weighted degree equals total coauthor occurrences under that contract. Zero-publication consistency, general averages, maximum/distinct/count bounds, and overflow-safe `BigInt` products are checked. Floating tolerance: `max(1e-12, 4 * ulp(expected))`.
6. Typed `CoauthorshipProperties` holds ordered collaboration years and a distinct multiwork vector. Duplicate text keys and reserved coauthorship text keys fail.
7. Tagged `GraphSourceEvidence.Work` and `SourceRecord` support work evidence and real portfolio source records. Source-record pointers match provenance source, record, and snapshot. The ORCID wire fixture cites committed employment `/0000-0002-4414-6920/employment/19198978`.
8. Work-evidence edge hashes preserve existing IDs. Source-record evidence hashes a compact JSON array as the final field of the existing LF-separated formula.
9. Shared strict reference parsers serve records, nodes, and endpoints. AUTHORED permits a researcher or unresolved mention pointing to a work.
10. A byte-identical `.conf` copy packages the authorized JSON HOCON subset. General HOCON/YAML support is not claimed; no dependency or build edit occurred.

COMMANDS RUN / OWNER-REPORTED TEST RESULTS:

All sbt runs used `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`, sbt 1.10.7, Homebrew Java 17.0.20.1.

- `sbt -batch 'core/Compile/scalafmt' 'core/Test/scalafmt' 'core/Test/compile'`: initial sandbox attempt failed before loading due to `~/.sbt/boot/sbt.boot.lock`; escalated retry compiled main but test compilation failed on a `fromConf` scope error, then corrected.
- `sbt -batch 'core/Compile/scalafmt' 'core/Test/scalafmt' 'core/test'`: initial test compilation failed on two ambiguous overloads; corrected with explicit GraphEdge type parameters. Next run executed 73 tests, 72 passed and one frozen wire example failed because its optional object was an array; corrected. Next run passed all 73 tests.
- Final: `sbt -batch 'core/Compile/scalafmt' 'core/Test/scalafmt' 'set core / Test / fork := true' 'core/testOnly edu.uic.cs441.scholarchain.core.ContractRepairSpec' check`: exit 0. Fresh-JVM repair suite 23/23 passed; full core check 77/77 passed; build verification 2/2 passed. Expected nested check failure was asserted by its parent test; marker ran afterward. Reported completion 2026-10-05 21:41:50 local. Fork setting was session-only.
- `git diff --check`: exit 0.
- `cmp modules/core/src/main/resources/scholarchain.config.v1.conf modules/core/src/main/resources/scholarchain.config.v1.json`: exit 0.
- Source search found no bibliography registry or old URI-authority helper.

The 23 new tests cover independent/fresh/parallel contexts, order and snapshot isolation, missing context, later-run lineage, shared DOI across source observations, spoofed bibliography, native OpenAlex and simultaneous DOI/arXiv, omitted Crossref DOI, author membership/team order, fractional and zero metrics, floating rounding and overflow, typed multiple-work properties, malformed/duplicate wire properties, ORCID pointers/hashes, strict reference IDs, and both AUTHORED endpoint forms.

ASSUMPTIONS: Phase 3 wire schemas are unaccepted drafts; labels remain unchanged. JSON HOCON profile is human-authorized. ROR validation checks identifier syntax, not registry membership or checksum.

RISKS: Typed graph evidence/properties change the draft wire representation; callers must adopt it and supply explicit work context. Syntax and provenance consistency cannot prove external factual content or authorize identity merges. Metric equality requires the declared complete canonical population. Conflicting source observations require upstream selection rather than implicit overwrite.

MANUAL ACTION REQUIRED: Coordinator gate replay, independent review, then human acceptance.

BLOCKED-ON OWNER: none.

BLOCKED-ON EVIDENCE: none for the owner handoff.

NEXT GATE: Fresh independent code reviewer; this report does not approve Phase 3.

## Ninth-review targeted domain follow-up

STATUS: COMPLETE for implementation and owner gates; independent review pending. OWNER: `/root/phase3_domain_repairs`, `domain-engineer`.

WORK ORDER: Repair the two P2 findings returned by the independent reviewer. FILES CREATED: none. FILES MODIFIED: `DomainValidation.scala` and `ContractRepairSpec.scala` under core. No wire, hash formula, build, dataset, control, or phase-report files were edited by the owner.

CHANGES: Total coauthor occurrences of zero require exactly zero average and weighted degree, including multiple solo publications. Nonzero rounding tolerance remains. Coauthorship work evidence must be a representative supporting work; AUTHORED evidence must identify its work target, and PUBLISHED_IN/HAS_TOPIC evidence its work source. Generic DERIVED_FROM/SUPPORTED_BY may cite a separate supporting work; typed source-record evidence is preserved.

COMMANDS RUN / TEST RESULTS: `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home sbt -batch 'core/Compile/scalafmt' 'core/Test/scalafmt' 'core/testOnly edu.uic.cs441.scholarchain.core.ContractRepairSpec' check`: exit 0 with sbt 1.10.7 / Homebrew Java 17.0.20.1. Targeted suite 27/27, full core 81/81, build verification 2/2, zero failures. Expected injected failure probe passed its parent test and marker ran. Owner-reported completion 2026-10-05 21:47:06 local. `git diff --check` exited 0. No failed runs in this round.

Four new tests cover solo positive-publication counts, tiny nonzero violations, unrelated evidence with recomputed stable ID, positive multiwork membership, publication endpoints, and generic independent supporting-work relations. All prior 77 tests remain.

ASSUMPTIONS: Generic provenance relations may use independent supporting works; publication-specific relations identify the publication whose facts they carry.

RISKS: Reference consistency cannot independently prove external content or identity decisions. MANUAL ACTION REQUIRED: Fresh read-only review and human acceptance. BLOCKED-ON OWNER/EVIDENCE: none for owner handoff. NEXT GATE: `/root/phase3_final_repair_review`; no self-approval or commit/push.

## ORCID notes-only follow-up

STATUS: COMPLETE. OWNER: `/root/phase3_dataset_notes_fix`, `dataset-engineer`. FILE MODIFIED: `datasets/schemas/orcid-record.md` only. The owner parsed narrow fields in the current ORCID worktree sample and confirmed the names, Ringgold employment identifier 4365, two education entries, Scopus ID 55497628100, and empty email/funding arrays. Those facts already matched the current note when the owner read it.

The owner corrected the remaining DOI coverage from one group to five of 11 groups (indexes 0, 1, 2, 3, 7), added mapping notes for researcher external IDs, education, and work DOI linkage, and accurately described the sample as a current worktree file. `git show HEAD:datasets/samples/orcid/records.jsonl` failed because the sample is untracked. No sample, checksum, script, or core changes occurred; no behavior tests were needed for this notes-only correction. The final fresh reviewer verified the facts and returned APPROVE with no blockers.

## Phase 17 coordinator index note (added 2026-11-22, package 17G; not part of the copied owner report)

The reports above combine some labels (for example "COMMANDS RUN / TEST RESULTS"). The same content under the standard labels:

COMMANDS RUN: see the "COMMANDS RUN / OWNER-REPORTED TEST RESULTS" and "COMMANDS RUN / TEST RESULTS" entries above, and the commands in `test-report.md`.
TEST RESULTS: see the same entries above and `test-report.md` (coordinator validation).
VALIDATION RESULTS: see the "VALIDATION RESULTS / CONTRACT CHOICES" entry above and `test-report.md`.

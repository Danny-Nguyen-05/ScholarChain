# Phase 3 repairs

Review verdicts are in `review.md`. Each repair was routed to the named owner. The coordinator did not edit implementation files.

## Rounds before the sixth review

- Dataset findings on the DBLP release claim, range byte cap, XML entities, `&amp;`, and `__pycache__` cleanup were repaired by `dataset-engineer` agents `6cf63f2d-aa97-4aa9-9e3d-aa9b70e3c67e`, `9e4cca17-cec1-4d2b-82ff-b379a0790452`, and `d9975e75-81ce-4481-a37a-cca4780ce6a6`. The fourth review resolved the October 2026 DBLP release against the official artifact page. Provenance is `datasets/provenance/dblp-snapshot-2026-10-03-dagstuhl.txt`.
- `.gitignore` rules `__pycache__/` and `*.pyc` were added by `build-engineer` `c20c18fb-0588-4471-8543-019cf171e2f9`. `git check-ignore` matched `.gitignore:24` and `.gitignore:25`.
- Domain findings through the fifth review (conflict outcome, pair and provenance agreement, ordinals, evidence IDs, DOI and arXiv pairs, authorship position, publication-team mentions) were repaired by `domain-engineer` agents `72baaa1e`, `8ddbe436`, `c4fd184f`, `fdc3b14c`, and `db0e7353`. The last of those reported 44 core tests before the sixth review.

## Sixth-review repairs

Dataset owner `a2ab7fcc-f51e-46e9-9069-b6173ec85778`:

- API `http_get` uses a 512 KiB hard cap and rejects oversized `Content-Length` or body bytes.
- DBLP sample DOCTYPE is `<!DOCTYPE dblp []>`. Sample SHA-256 updated to `e23d50c04b2cadcc01ff719ea1841157f2d865dd0e2657b27d3bd4931fe2a935`.
- ORCID schema note now matches the DOI in `works.group[7]`.

Domain owner `4ca492d9-7777-4970-a10f-1a75ba15b238`:

- Metrics fixture average and maximum coauthors are 1, and contradictory counts fail validation.
- Duplicate team mentions fail, and `teamSize` must equal the distinct member count.
- Pair binding no longer accepts a jointly rewritten `workId` and `doi`.
- Graph-path evidence requires `graphPath` and a matching ID. Metric and edge evidence have locator fields.
- Graph edges reject malformed endpoints and non-numeric coauthorship counts.
- Crossref `sourceRecordId` must match the work DOI.
- Config graph years must be in 1..9999.
- `modules/core/src/main/resources/scholarchain.config.v1.json` is the versioned file loaded by `ConfigLoaderSpec`.

Coordinator evidence for review item 12: this file, `prompt.md`, and `owner-report.md`. `review.md` and `test-report.md` were already present. `human-gate.md` and `accepted-commit.md` remain unwritten.

Coordinator re-run after these repairs: dataset regenerate, manifest validation, 6 Python tests, four checksums, and `sbt -batch check` all exited 0. Counts are in `owner-report.md`.

## Eighth-review repair delegation

The human authorized delegated implementation of the eight current findings. `/root/phase3_domain_repairs` is the sole writer for `modules/core/**`. The coordinator owns this phase evidence; `/root/phase3_repair_test_audit` advises on acceptance cases read-only. A fresh independent reviewer will inspect the final implementation after the owner finishes. The work order is appended to `prompt.md`.

STATUS: IN_PROGRESS. The targets are pure explicit work binding, source identifier consistency, complete metric invariants, graph property/source-evidence representation, and reference node ID validation. Results will be appended from the owner's report and independently observed checks. No human gate or accepted commit is claimed.

### Independent acceptance audit

Read-only `/root/phase3_repair_test_audit` supplied positive and adversarial cases before final review: explicit source/record/snapshot binding, independent contexts and call order, valid downstream run IDs, authoritative URI conflicts, missing Crossref DOI, zero and fractional multi-publication metrics, duplicate graph properties, multiwork encoding, ORCID source evidence, canonical researcher and unresolved mention AUTHORED endpoints, and strict shared reference ID parsers. The coordinator routed that checklist to the owner.

Two interpretations were corrected without inventing human approval: a derived pipeline run can differ from the source WorkRecord run; work binding must identify the source observation rather than universally equate run IDs. Weighted degree equals total coauthor occurrences only under a declared complete canonical graph population; the owner must state the metric population contract. The [primary HOCON specification](https://github.com/lightbend/config/blob/main/HOCON.md) permits JSON syntax, and the existing human work order explicitly authorizes that profile. JSON-only syntax support is a documented limitation, not by itself a missing config file or malformed config defect.

### Implementation handoff

STATUS: Implementation COMPLETE; independent review pending. The sole domain owner repaired the eight findings and related acceptance cases within `modules/core/**`. Chosen contracts, changed paths, initial failures and successful owner checks are appended to `owner-report.md`. The owner added 23 tests, including a fresh-JVM run. Coordinator replay passed 77 core tests, 2 build tests, 6 Python tests, manifest validation, and four sample hashes; see `test-report.md`.

`/root/phase3_repaired_code_review` is the fresh read-only reviewer. The coordinator will route any concrete findings back to the same owning agent and assemble the verdict here and in `review.md`. No human acceptance, commit, or push is recorded by this repair handoff.

### Ninth-review follow-up

The independent reviewer returned two P2 findings after confirming the eight original areas: exact zero for all-solo metrics and coauthorship work evidence membership. The coordinator routed both to `/root/phase3_domain_repairs`, the sole core writer, with positive/negative regression tests and formatting/check requirements. Full findings are in `review.md`; repairs are pending.

The owner completed both follow-up repairs in two core files, added four regressions, and reported 27 targeted, 81 full core, and 2 build tests passing. Complete command evidence is appended to `owner-report.md`. Fresh `/root/phase3_final_repair_review` reviews this finished follow-up read-only. Final coordinator replay and reviewer verdict are pending at this handoff.

### Completed delegated repair gate

STATUS: COMPLETE for the authorized implementation, validation, and independent review. `/root/phase3_final_repair_review` returned APPROVE after verifying both follow-ups and all eight earlier repair areas. Final coordinator check passed 81 core tests and 2 build tests; dataset gates passed 6 Python tests, four-dataset validation, sample verification, and four checksums. Full source/report evidence is linked through the phase reports.

NEXT GATE: Human Phase 3 acceptance. The coordinator implemented no application files, wrote no human gate, and made no commit or push.

### Final readiness review and minor follow-up

The human requested a fresh review and directed that minor nonblocking items not hold Phase 3. The dataset owner corrected remaining ORCID notes against the current sample without changing its bytes or any code. `/root/phase3_acceptance_review` returned APPROVE for readiness with no blockers. Optional DBLP Content-Range offset/body-length consistency is recorded as a nonblocking dataset-owner follow-up in `review.md`. Existing 81-core/2-build and dataset gates apply because this pass changed notes only. Human acceptance and commit remain separate.

## Eleventh-review schema repair

The eleventh review returned one P3: `datasets/schemas/orcid-record.md` contradicted `datasets/samples/orcid/records.jsonl`. The human asked the coordinator to route it. [Fix ORCID schema notes](f864e1c4-07df-46ad-9c07-7029074969d3), `dataset-engineer` on `inherit` (this session’s Grok 4.7), edited only that schema note.

STATUS: COMPLETE for this documentation repair. Not a Phase 3 acceptance.

The note now records given-names `Charles Claiborne`, family-name `Rice`, credit-name `Claiborne Rice`, employment `19198978` as RINGGOLD `4365`, education put-codes `19198991` and `19198994`, and Scopus Author ID `55497628100`. Email and funding remain absent. The `group[7]` DOI note is unchanged.

Owner-observed checks: a post-edit path comparison reported 52 checks and 0 failures; `validate_datasets.py` printed `OK: manifest (4 datasets), samples, and script bounds validated`; `shasum -a 256 -c samples/SHA256SUMS` reported all four samples OK. The coordinator had already parsed the same JSONL fields before this handoff and reread the edited note; those examples match. The coordinator did not re-run `sbt check`. Sample bytes were not rewritten.

NEXT GATE: A fresh read-only review of this schema note, only if the human asks. Human acceptance, `human-gate.md`, and any commit or push remain separate.

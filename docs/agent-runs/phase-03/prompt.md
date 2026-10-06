# Phase 3 work order

The human architect assigned the coordinator to spawn `dataset-engineer` and `domain-engineer` in separate contexts, then a read-only `code-reviewer`. The coordinator does not implement dataset or domain files. Models used for implementation: `dataset-engineer` `composer-2.5-fast`; `domain-engineer` `inherit` for the first contract pass, then `composer-2.5-fast` for later repairs. The fresh review after the sixth-review repairs uses `inherit`.

Checkout at the start of Phase 3: `main` at `61d1ebdf31e636d502343418ebdd6efdad95e3ed`. Phase 1 and Phase 2 were accepted. Do not edit Phase 1 control files or Phase 2 build files except the later human-routed `.gitignore` bytecode rules, which belong to `build-engineer`.

## Dataset-engineer

Own only `datasets/**`. Select DBLP plus at least three additional real open scholarly datasets. Create `datasets/dataset-manifest.yaml`, bounded idempotent scripts under `datasets/scripts/`, legally redistributable samples under `datasets/samples/`, schema notes under `datasets/schemas/`, and license notes. Record source, official URL, license evidence, pinned snapshot, format, size, S3 prefix plan, checksum coverage, subset rule, schema, linkage keys, update method, limitations, privacy, and validation commands. Compute real sample checksums. Do not invent an unavailable upstream checksum. Do not download a full corpus or access AWS.

## Domain-engineer

Own only `modules/core/**`. Implement the immutable Scala 3 records named in the course Phase 3 section, stable IDs, pair ordering, schema versions, enums, provenance, and configuration loading from environment variables plus a versioned JSON file read as the HOCON profile. Use existing uPickle and ScalaTest. Do not edit `build.sbt` or `project/**`. If a new parser is required, return `BLOCKED-ON`.

## Later human repair orders

Subsequent `REQUEST_CHANGES` verdicts are recorded in `review.md`. Each was routed only to the named owner. The sixth-review repair order is the latest: domain findings 1–7 and 11, dataset findings 8–10, and coordinator evidence files for item 12. Do not commit or push. Do not write `human-gate.md` or `accepted-commit.md`. Do not create `validation.md`.

## Authorized repair delegation after the eighth review

Exact user request: "so can you trigger subagents, to fix those for me?"

The coordinator assigned `/root/phase3_domain_repairs` as the sole writer for `modules/core/**`. The work order is to repair all eight eighth-review domain findings, remove process-global bibliography state, and use explicit validated work inputs or immutable scoped context for pair, authorship, and team binding. Reject conflicting source identifiers, enforce complete collaboration metric relationships, validate graph property uniqueness and years, define a multiwork representation, allow source records such as ORCID as graph evidence, and validate reference node IDs. Update positive and adversarial contract tests and wire examples; verify order independence, snapshot isolation, multiple works, and valid ORCID affiliation evidence. Return a structured owner report and run formatting and `sbt check` on Java 17. The owner edits no dataset, build, constitutional, or phase-report files.

The coordinator assigned `/root/phase3_repair_test_audit` as a read-only code reviewer to independently check the repair acceptance cases and the interpretation of the prior findings. After implementation, a fresh read-only code reviewer will inspect the complete repairs. The coordinator assembles phase evidence and reruns relevant gates. Human acceptance and any commit/push remain separate gates.

The existing human-authorized JSON HOCON profile remains the config scope. No general HOCON or YAML parser support is claimed, and no new parser dependency is authorized by this work order.

# 11A pre-edit inventory and gap decisions

The test specialist returned this inventory before implementation; the coordinator authorized the bounded additions afterward. Existing generated JUnit XML was inspected, not rerun: 1,216 tests in 149 reports, zero failure/error/skip (baseline-test-counts.json).

Existing tests already covered malformed/entity/split XML, DOI duplicate/conflict records, author ordering, ambiguous/conflicting endpoints, empty/disconnected graphs, missing evidence and output gates. The initial gap list selected:

- NFC versus NFD, Latin/Cyrillic confusables and distinct DBLP homonym suffixes, with original observation text retained.
- A larger team with repeated common names: 64 mentions, 2,016 unique ordinal pairs and 63 incidences per ordinal; atomic overflow rejection.
- A substantially oversized blocking group: 257 observations against max eight, plus a downstream candidate-join bypass and exact pair-budget boundary.
- New C5 ring, barbell, clique with pendant nodes and isolate graph shapes, with hand-derived all-node degree/weighted degree/core/component values, shortest paths and fixed-partition bridges.
- Real candidate-job replay with reordered input and identical sorted-row SHA-256, retaining exact completeness assertions.

During test authoring, explicit final-record truncation, multiline Unicode title and sparse-metadata assertions were added. The final 15-test allocation is eight parser/identity/team/metadata, four blocking/replay and three graph cases.

The final coverage map reuses 30 distinct existing named tests alongside those 15 additions. Four existing ER/resolver common-name cases were added to the report mapping after a coordinator completeness check; their committed source was unchanged. Counts describe selected mapping coverage, not an exhaustive census of every relevant historic case. Exact names and per-category counts are in coverage.json and coverage-validation.json.

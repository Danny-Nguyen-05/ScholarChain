# Crossref REST `/works` response

**Schema version:** `scholarchain.crossref-works-schema.v1`. This is the ScholarChain schema-note
version; it is the value of `schema_version` for the `crossref` entry in
`datasets/dataset-manifest.yaml`. It describes the REST API response in the committed sample
`samples/crossref/works.jsonl` (one `work` response for DOI `10.1007/978-3-642-31674-6_1`),
retrieved on 2026-10-05 (acquisition index id `crossref-rest-2026-10-05`).

**Upstream version:** Crossref REST API response envelope `message-type` `work`,
`message-version` `1.0.0`, as recorded in the sample `samples/crossref/works.jsonl`. No Crossref
public data file snapshot is pinned in the repository; this note was written against the
2026-10-05 sample.

**Documentation:** https://www.crossref.org/documentation/retrieve-metadata/rest-api/

## Fields present in `samples/crossref/works.jsonl`

The committed line stores the API JSON object with a `message` field for DOI
`10.1007/978-3-642-31674-6_1`.

Observed `message` fields include: `DOI`, `type`, `title`, `author` (with `given`,
`family`, `affiliation`, `sequence`), `publisher`, `published-print`,
`published-online`, `page`, `ISBN`, `container-title`, `link`, `license`, `funder`,
`reference-count`, `is-referenced-by-count`, `subject`, `created`, `indexed`.

## Mapping notes

| Crossref field | ScholarChain use |
| --- | --- |
| `DOI` | Authoritative work join key |
| `title[]` | Title normalization |
| `author[]` | Author mention sequence |
| `published-* .date-parts` | Year/window filters |
| `funder[]` | Enrichment (not required for coauthor graph) |
| `license[]` | Redistribution constraints for abstracts/PDFs |

## Not present in committed sample

ORCID on authors, abstract text, full reference list bodies, clinical trial links.

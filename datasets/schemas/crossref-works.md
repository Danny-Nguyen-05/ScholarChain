# Crossref REST `/works` response

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

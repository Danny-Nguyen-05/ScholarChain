# OpenAlex Work object (API JSON)

**Schema version:** `scholarchain.openalex-works-schema.v1`. This is the ScholarChain schema-note
version; it is the value of `schema_version` for the `openalex` entry in
`datasets/dataset-manifest.yaml`. It describes the Work object in the committed sample
`samples/openalex/works.jsonl` (one Work, 51 top-level keys), retrieved from the live OpenAlex
REST API on 2026-10-05 (acquisition index id `openalex-rest-2026-10-05`).

**Upstream version:** upstream version not recorded; written against the 2026-10-05 live REST API
sample `samples/openalex/works.jsonl` (the Work's own `updated_date` is `2026-09-25T08:18:29.962427`).
No OpenAlex API version or bulk snapshot date is pinned in the repository
(`datasets/dataset-manifest.yaml`, `snapshot_or_version`).

**Documentation:** https://help.openalex.org/data/works/ and https://api.openalex.org/works/{id}

## Fields present in `samples/openalex/works.jsonl`

Observed top-level keys include (51 total): `id`, `doi`, `display_name`, `title`,
`publication_year`, `publication_date`, `type`, `ids`, `language`, `primary_location`,
`open_access`, `authorships`, `concepts`, `topics`, `keywords`, `biblio`,
`cited_by_count`, `created_date`, `updated_date`, `abstract_inverted_index`, and
additional metric/count fields.

Within `authorships[]` the sample includes `author_position`, `author.id`,
`author.display_name`, `author.orcid`, `institutions[]` (with `display_name`, `ror`,
`country_code`), and `raw_author_name`.

## Mapping notes

| OpenAlex field | ScholarChain use |
| --- | --- |
| `id` | OpenAlex work identifier |
| `doi` | Primary join key to DBLP `ee` and Crossref |
| `authorships[].author.id` | Author candidate identifier (not ground truth) |
| `authorships[].author.orcid` | Identity evidence when present |
| `topics` / `concepts` | Topic enrichment filters |
| `authorships[].institutions[]` | Institution enrichment |

## Not present in committed sample

OpenAlex author entity fetch, full citation graph, S3 snapshot partition paths.

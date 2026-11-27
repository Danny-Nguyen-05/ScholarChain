# ORCID public record (JSON)

**Schema version:** `scholarchain.orcid-record-schema.v1`. This is the ScholarChain schema-note
version; it is the value of `schema_version` for the `orcid` entry in
`datasets/dataset-manifest.yaml`. It describes the public record in the committed sample
`samples/orcid/records.jsonl` (one record, ORCID `0000-0002-4414-6920`), retrieved from the
ORCID public API on 2026-10-05 (acquisition index id `orcid-public-api-2026-10-05`).

**Upstream version:** ORCID public API `v3.0`, record endpoint `GET /v3.0/{orcid}/record`
(`datasets/scripts/acquire_samples.py`, `refresh_orcid`; `datasets/dataset-manifest.yaml`,
`bounded_subset_rule`). The annual Public Data File date is not pinned in the repository, and no
finer ORCID API release is recorded; this note was written against the 2026-10-05 sample.

**Documentation:** https://info.orcid.org/documentation/api-tutorials/api-tutorial-read-data-on-a-record/

## Fields present in `samples/orcid/records.jsonl`

Record ORCID `0000-0002-4414-6920` (retrieved 2026-10-05):

| Path | Example / note |
| --- | --- |
| `orcid-identifier.path` | `0000-0002-4414-6920` |
| `person.name.given-names.value` | `Charles Claiborne` |
| `person.name.family-name.value` | `Rice` |
| `person.name.credit-name.value` | `Claiborne Rice` |
| `person.external-identifiers.external-identifier[0]` | type `Scopus Author ID`, value `55497628100` |
| `history.claimed` | `true` |
| `activities-summary.employments.affiliation-group[0].summaries[0].employment-summary` | put-code `19198978`; organization `University of Louisiana at Lafayette`; `disambiguated-organization-identifier` `4365`; `disambiguation-source` `RINGGOLD` |
| `activities-summary.educations.affiliation-group[0].summaries[0].education-summary` | put-code `19198991`; organization `University of Georgia`; `disambiguated-organization-identifier` `https://ror.org/00te3t702`; `disambiguation-source` `ROR` |
| `activities-summary.educations.affiliation-group[1].summaries[0].education-summary` | put-code `19198994`; organization `University of Chicago`; `disambiguated-organization-identifier` `https://ror.org/024mw5h28`; `disambiguation-source` `ROR` |
| `activities-summary.works.group[7].work-summary[0].external-ids.external-id` | DOI `10.1007/978-3-642-31674-6_1` (`external-id-type`: `doi`) on public work title `Machine Mentality?` |

## Mapping notes

| ORCID field | ScholarChain use |
| --- | --- |
| `orcid-identifier.path` | Validated external researcher ID candidate |
| `person.name.*` | Name features only; not proof of authorship on external works |
| `person.external-identifiers.external-identifier[*]` | Declared external researcher ID candidates, with their identifier type and source |
| Employment summaries | Affiliation evidence for blocking and match features |
| Education summaries | Education affiliation evidence for blocking and match features |
| Work summary DOI external IDs | Work linkage candidates across sources; not proof of researcher identity |

## Not present in current worktree sample

Email addresses and funding items. `person.emails.email` and
`activities-summary.fundings.group` are empty arrays.

The record includes 11 public `activities-summary.works.group` entries. Five groups
(`0`, `1`, `2`, `3`, and `7`) contain work summaries with DOI external IDs; six groups
do not. The work in `group[7]` carries DOI `10.1007/978-3-642-31674-6_1`, aligned with
the linked dblp/OpenAlex/Crossref portfolio DOI.

## Linkage

Matches dblp author tag `orcid="0000-0002-4414-6920"` on record `series/sapere/BerkeleyR13`.
Join to OpenAlex/Crossref in the portfolio uses DOI `10.1007/978-3-642-31674-6_1` for works.

# DBLP XML (committed sample mapping)

**Schema version:** `scholarchain.dblp-xml-schema.v1`. This is the ScholarChain schema-note
version; it is the value of `schema_version` for the `dblp` entry in
`datasets/dataset-manifest.yaml`. It describes the mapping of the committed sample
`samples/dblp/linked-records.xml` (three `inproceedings` records) from the DBLP XML monthly
snapshot `dblp-2026-10-03` (retrieved 2026-10-05).

**Upstream version:** DBLP XML snapshot `dblp-2026-10-03` (DOI `10.4230/dblp.xml.2026-10-03`), per
`datasets/provenance/dblp-snapshot-2026-10-03-dagstuhl.txt`. The DTD this note was written against
is `dblp-2023-06-28.dtd` (named in the upstream DOCTYPE example below and in
`datasets/schemas/dblp/dblp-named-entities.v1.tsv`); the DTD revision shipped with the 2026-10-03
snapshot is not recorded in the repository. The local character-entity catalogue is version `v1`
(`dblp-named-entities.v1.tsv`).

**Upstream schema:** DBLP DTD referenced by monthly full XML snapshots on Dagstuhl DROPS
(example upstream DOCTYPE: `<!DOCTYPE dblp SYSTEM "dblp-2023-06-28.dtd">`). Pinned upstream
gzip for bounded refresh: `dblp-2026-10-03.xml.gz` (DOI `10.4230/dblp.xml.2026-10-03`); filename,
MD5 `cbd329100ea1bbb2873fa2f6d414ea00`, and compressed size 1107081001 bytes are recorded in
`datasets/provenance/dblp-snapshot-2026-10-03-dagstuhl.txt` (quotes the Dagstuhl artifact File
section and HEAD on the storage URL).
Full DTD file: https://drops.dagstuhl.de/storage/artifacts/dblp/xml/2023/dblp-2023-06-28.dtd

Committed sample uses UTF-8 and a self-contained DOCTYPE (no network DTD fetch). When
extracted records contain DTD named entities (for example `&eacute;`), `acquire_samples.py`
adds an internal `<!DOCTYPE dblp [ ... ]>` subset with the ISO Latin-1 entity declarations
from the official DBLP DTD; otherwise it uses an empty internal subset `<!DOCTYPE dblp []>`.

## Approved local character-entity catalogue

`datasets/schemas/dblp/dblp-named-entities.v1.tsv` is the approved character-entity list
(the pairs in `datasets/scripts/dblp_entities.py` `DBLP_NAMED_ENTITIES`). Approved SYSTEM
basenames for the local catalogue are `dblp.dtd` and `dblp-YYYY-MM-DD.dtd` only. A SYSTEM
id with a scheme, `//`, backslash, `..`, or any other basename is not approved and must
not be retrieved. Entities absent from the catalogue stay unresolved; they are not fetched.
Predefined XML entities (`amp`, `lt`, `gt`, `quot`, `apos`) are not catalogue rows.

## Record types in committed sample

All three committed records are `inproceedings` elements.

## Fields present in `samples/dblp/linked-records.xml`

| DBLP element/attribute | ScholarChain-oriented use |
| --- | --- |
| `@key` | Stable dblp record key (`dblp_key`) |
| `@mdate` | Source modification hint |
| `title` | Work title normalization input |
| `author` (text) | Author mention string (not identity) |
| `author/@orcid` | Optional ORCID hint on mention |
| `year` | Publication year |
| `booktitle` | Venue / container label |
| `pages` | Pagination metadata |
| `ee` | External ID (often DOI URL) |
| `crossref` | Internal dblp cross-reference key |
| `url` | dblp internal HTML path |

## Linkage to enrichment sources

Primary linked DOI in sample line-up: `10.1007/978-3-642-31674-6_1` on record
`series/sapere/BerkeleyR13`. ORCID `0000-0002-4414-6920` appears on the second
author of that record.

## Not present in committed sample

Full `dblp.xml` corpus, `www` person pages, affiliation blocks, explicit DBLP
author PID elements (dblp only exposes author strings in these records).

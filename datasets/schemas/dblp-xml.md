# DBLP XML (committed sample mapping)

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

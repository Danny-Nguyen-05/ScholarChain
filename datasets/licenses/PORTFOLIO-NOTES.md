# Dataset license and provenance notes (Phase 3)

This file summarizes license evidence checked for the committed portfolio. It does
not replace per-entry fields in `dataset-manifest.yaml`.

| Dataset | License summary | Evidence URL checked |
| --- | --- | --- |
| DBLP | CC0 1.0 for metadata (ODC-BY 1.0 secondary) | https://dblp.org/faq/Under+what+license+is+the+data+from+dblp+released |
| OpenAlex | CC0 1.0 for OpenAlex data | https://github.com/ourresearch/openalex-docs/blob/main/license.md |
| ORCID | Public Data File CC0 1.0; public API subject to ORCID policies | https://info.orcid.org/public-data-file-use-policy/ |
| Crossref | Site/docs CC BY 4.0; API metadata use described on REST API page | https://www.crossref.org/documentation/retrieve-metadata/rest-api/ |

Committed samples were retrieved on **2026-10-05** except where upstream pages
only provide ongoing live API access (OpenAlex, ORCID public API, Crossref REST).

`acquisition-index.v1.json` is the processing snapshot identity for loaders. It
is derived from `dataset-manifest.yaml` and `provenance/dblp-snapshot-2026-10-03-dagstuhl.txt`.
Every source records retrieval date `2026-10-05`. That date is a bulk snapshot
date only for DBLP (`dblp-2026-10-03`, monthly XML). OpenAlex, Crossref, and
ORCID are live API retrievals (`openalex-rest-2026-10-05`,
`crossref-rest-2026-10-05`, `orcid-public-api-2026-10-05`). API retrieval dates
are not bulk snapshot dates.

Redistribution of committed samples is intended to align with the licenses above.
Downstream pipelines must still respect publisher copyright on abstracts and PDFs
when those appear in future pulls.

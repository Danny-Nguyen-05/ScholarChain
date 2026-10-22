# Phase 6 bounded DBLP slice

The user approved a local integration slice from **dblp-2026-10-03** (DOI
[10.4230/dblp.xml.2026-10-03](https://doi.org/10.4230/dblp.xml.2026-10-03)),
up to 20,000 publications from PODC, DISC, ICDCS, OSDI, SOSP, NSDI,
EuroSys and Middleware in 2005–2026 inclusive. Bibliographic metadata is
released under [CC0 1.0](https://dblp.org/faq/Under+what+license+is+the+data+from+dblp+released).
The repository's original upstream size/MD5 evidence is retained in
`datasets/provenance/dblp-snapshot-2026-10-03-dagstuhl.txt`.

The acquisition script first reuses a verified local archive; otherwise it
makes one request for the pinned official gzip. It enforces a cumulative
1,342,177,280-byte body budget and a 1,800-second acquisition deadline before
reading, validates the expected Content-Length, and makes no retries or
metadata requests. Socket reads have a timeout bounded by the remaining
deadline. A cap, truncation or checksum failure stops the run.
The complete gzip must have MD5 `cbd329100ea1bbb2873fa2f6d414ea00` and
1,107,081,001 bytes before any publication is selected. A SHA-256 is also
recorded. Partial downloads are retained in ignored `target/` for diagnosis;
they are never accepted as input.

Selection keeps the first 2,500 eligible `inproceedings` per venue in pinned
archive order, with the published year in 2005–2026. DISC is keyed by DBLP's
`conf/wdag/` series; `conf/disc/` is also recognized. This yields at most
20,000 records and includes every venue with eligible records. This is a
convenience slice with source-order and per-venue-cap bias, suitable for
pipeline integration and observed runtime checks. It is not a statistically
representative sample of DBLP or distributed systems. A work is included
by its own venue/year; the slice does not close over its authors' other works.

The output XML preserves record content/order, replaces DBLP Latin-1 named
entities with numeric XML references, and has no external DTD dependency.
It is accepted by the unchanged Hadoop DBLP input format. Full source and
selected XML payloads remain under ignored `target/phase6-inputs/6fg-dblp/`.
The committed `dblp-slice-manifest.v1.json` records checksums, counts, exact
selection rules, bias, provenance, and retrieval measurements.

Run from the repository root (Python 3 standard library only):

```sh
python3 datasets/scripts/phase6/test_dblp_slice.py
python3 datasets/scripts/phase6/acquire_dblp_slice.py
```

For a repeat extraction from the retained verified archive, supply new output
and manifest paths using `--output` and `--manifest`. Existing output and
manifest files are refused rather than overwritten. The generated manifest's
time and local paths are observational metadata; selected XML bytes and
selected-key hashes are deterministic.

Hadoop's configured team limit is a separate preparation policy. The slice
retains original author lists, including any lists larger than that limit;
its manifest reports team-size counts so excluded Hadoop teams can be
accounted for explicitly by the pipeline run.

The observed archive retrieval is retained separately in
`dblp-archive-acquisition.v1.json`: one 1,107,081,001-byte download in
244.720 seconds, without retries or redirects. Initial extraction exposed
adjacent XML records sharing a line; the corrected bounded tag scanner is
covered by chunk-boundary regression tests and used the verified local
archive with zero additional network. To retain the acquisition receipt in
a fresh extraction manifest, pass:

```sh
python3 datasets/scripts/phase6/acquire_dblp_slice.py \
  --output target/phase6-inputs/6fg-dblp/fresh.xml \
  --manifest target/phase6-inputs/6fg-dblp/fresh-manifest.json \
  --acquisition-receipt datasets/phase6/dblp-archive-acquisition.v1.json
```

Observed selection: 10,577 publications, 21,819 exact author strings, all
22 years and all eight venues. The largest author list has 71 entries;
63 records exceed 16 authors, five exceed 32, and 21 have no author element.
Those rows remain in the raw slice for the existing Hadoop input validation
and counter policy. They are not silently removed by acquisition.
The actual replay reproduced identical XML bytes and selection metadata;
its payload and manifest remain in ignored `target/`.

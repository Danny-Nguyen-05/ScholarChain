# ScholarChain AI review drafts — batch 12 (tasks 221–240)

> **Status: AI_SUGGESTIONS_PENDING_HUMAN_REVIEW.** These are AI-generated suggestions from a session-reported `claude-opus-5-5` model (not independently verified). They are not human reviews or gold labels. Record your own decision in each task's decision box; an empty box means not reviewed.

Queue: `review-queue:05c5817f62a70d378829be361b9c9169fc9af18448f7c83c245f1d65bbca6175`  
Work tasks: 14 · Researcher tasks: 6

Rows marked `>> … <<` in the raw data and the 'Name as written' row identify the mention being compared. OpenAlex author IDs and OpenAlex-supplied ORCIDs are provider hypotheses. Lines in _italics_ starting with 'helper:' are exact-string comparisons computed by a script to help reading; they are not judgments.

---
## Task 221 — Work

- **pairId:** `resolution-pair:4fcca275e8f8c499e075b2235faefd8f462be813bb5549af66e3c1617cf0db8b`
- **evidenceHash:** `6f666055fb747a9c2b05e44da6d46d8eb8f14800e82d6695fd06c8007f044e6f`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3103950664 (article) | OPENALEX W4387321503 (conference-paper) |
| Title | Fault-tolerant and transactional stateful serverless workflows | Paella: Low-latency Model Serving with Software-defined GPU Scheduling |
| Year | 2020 | 2023 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4306420989 |
| DOI | — | 10.1145/3600006.3613163 |
| arXiv ID | — | — |
| Pages | 1187-1204 | 595-610 |
| Authors | (5) Haoran Zhang, Adney Cardoza, Peter Baile Chen, Sebastian Angel, Vincent Liu | (3) Kelvin K. W. Ng, Henri Maxime Demoulin, Vincent Liu |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3600006.3613163, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3600006.3613163, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.1145/3600006.3613163'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Fault-tolerant and transactional stateful serverless workflows" (no DOI, OSDI 2020) and B "Paella: Low-latency Model Serving with Software-defined GPU Scheduling" (10.1145/3600006.3613163, 2023) have different titles and years; only Vincent Liu is shared.

**Supporting evidence:**
- work.title different
- work.year 2020 vs 2023
- Author lists otherwise disjoint (5 vs 3)

**Conflicting evidence:**
- Shared author Vincent Liu

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:a51a7d1dccfd085f01289aa5f94d4fdc5b557daecfd203f58d72be58d59749ae` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:229`
- B `work` `er-evidence:6f072eed471b3ff7ec86adfb260e85d88fb7b0991218f1807f8617df9d00ba94` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:71`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 222 — Work

- **pairId:** `resolution-pair:bef6d447b454c3167809476f55233523585ae0d68fae2a07265c071946c4ca35`
- **evidenceHash:** `26dd6f3ca5cf8d50b1f9125d27377547b25c7e604ddb524d804bb0c38f31a14e`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0001-7793-9049/work/104452170 | ORCID activity 0000-0003-0832-116X/work/151681291 |
| Title | A Formal Framework for Complex Event Recognition | A Formal Framework for Complex Event Recognition |
| Year | publicationYear=2021 | publicationYear=2021 |
| Venue ID | — | — |
| DOI | 10.1145/3485463 | 10.1145/3485463 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0001-7793-9049 (author list not supplied) | ORCID record owner 0000-0003-0832-116X (author list not supplied) |
| Observed identifiers | doi=10.1145/3485463 (self) | doi=10.1145/3485463 (self); wosuid=WOS:000728453500004 (self) |

_helper: normalized DOI A=['10.1145/3485463'] B=['10.1145/3485463'] -> equal_

**AI-proposed label: `same`**

**Note:** ORCID activities from two different ORCID records (0000-0001-7793-9049 and 0000-0003-0832-116X) both carry DOI 10.1145/3485463, the identical title "A Formal Framework for Complex Event Recognition" and publicationYear 2021, consistent with one co-authored publication listed by two people.

**Supporting evidence:**
- Normalized observedDoi equal: 10.1145/3485463
- Identical title
- Same year 2021

**Conflicting evidence:**
- Different ORCID record owners (expected for co-authors, not a conflict about the publication)

**Limitations / missing information:**
- No author list, venue or pages in ORCID activities

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:79f0e9abc28bcf92d80e141cc519baf4f0ae3ba5aaacb1236c1b1972b71ccdee` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:215`
- B `orcid-activity` `er-evidence:2157607120df1a9dd4bb652a686b0a175cf281faa23667b0ba721321131ced27` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:318`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 223 — Work

- **pairId:** `resolution-pair:2ab5de232610f4aff76ef2c29623a7949c899e9aad5a6a76806e93e66367eac6`
- **evidenceHash:** `cd45eae27e5fe607eba15dd8a2c7e0837bbdaeb5e0b014e1eba6050f89dc996f`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | CROSSREF 10.1145/3277006.3277012 (journal-article) | OPENALEX W2890777401 (article) |
| Title | Technical Perspective: | Technical Perspective: |
| Year | 2018 | 2018 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S47508943 |
| DOI | 10.1145/3277006.3277012 | 10.1145/3277006.3277012 |
| arXiv ID | — | — |
| Pages | 23-23 | 23-23 |
| Authors | (1) Yannis Papakonstantinou | (1) Yannis Papakonstantinou |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3277006.3277012, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3277006.3277012, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3277006.3277012'] B=['10.1145/3277006.3277012'] -> equal_

**AI-proposed label: `same`**

**Note:** Crossref and OpenAlex records share DOI 10.1145/3277006.3277012, title "Technical Perspective:", year 2018, page 23-23 and sole author Yannis Papakonstantinou.

**Supporting evidence:**
- Normalized DOI equal
- Identical (truncated) title, year, pages and author

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- Title truncated in both sources

<details><summary>Evidence references</summary>

- A `work` `er-evidence:2d5dd696d9ecc8c8933392579e8b47e36bbb575f5fd12fb1856c20ffb3c2498c` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:4`
- B `work` `er-evidence:1528db96866fb4c2aab81b13ceb2fc199d698437e6c44e8e9b89cdb39c8fd45a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:397`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 224 — Work

- **pairId:** `resolution-pair:99f125d5a43bbbd12feb842186f8ea1708db806d2a137574ed2612a97848f1d7`
- **evidenceHash:** `07f438c0265ed9d4cdd07f9492ee84ee53f34b39ba687e8e409aff1d3671cdae`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | CROSSREF 10.1145/3299887.3299894 (journal-article) | OPENALEX W2904240362 (article) |
| Title | Kenneth Ross Speaks Out on Making Contributions that Span Technology and Science | Kenneth Ross Speaks Out on Making Contributions that Span Technology and Science |
| Year | 2018 | 2018 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S47508943 |
| DOI | 10.1145/3299887.3299894 | 10.1145/3299887.3299894 |
| arXiv ID | — | — |
| Pages | 41-47 | 41-47 |
| Authors | (2) Marianne Winslett, Vanessa Braganholo | (2) Marianne Winslett, Vanessa Braganholo |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3299887.3299894, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3299887.3299894, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3299887.3299894'] B=['10.1145/3299887.3299894'] -> equal_

**AI-proposed label: `same`**

**Note:** Crossref and OpenAlex records share DOI 10.1145/3299887.3299894, the title "Kenneth Ross Speaks Out on Making Contributions that Span Technology and Science", year 2018, pages 41-47 and authors Marianne Winslett and Vanessa Braganholo.

**Supporting evidence:**
- Normalized DOI equal
- Identical title, year, pages and author list

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:435803cb72545c2b6fe5eeea2c3603e41607ed58676a0bd76902b2743ebae8f3` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:8`
- B `work` `er-evidence:e37e42faa01c64149e203ab862b90907c25e0c46fa6740a60846ef43ecc3d6a5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:371`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 225 — Work

- **pairId:** `resolution-pair:1cfcabc37b7fe1768815f32f0f1fe39dc06fb243b9b9dc3f8829ffa3e24cc953`
- **evidenceHash:** `39b20d046b97eb110723ada7ae4c52910125f6589d574b9e776b860da6340703`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0001-7793-9049/work/125716572 | ORCID activity 0000-0003-0832-116X/work/151681303 |
| Title | CORE: a complex event recognition engine | CORE: a Complex Event Recognition Engine |
| Year | publicationYear=2022 | publicationYear=2022 |
| Venue ID | — | — |
| DOI | 10.14778/3538598.3538615 | 10.14778/3538598.3538615 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0001-7793-9049 (author list not supplied) | ORCID record owner 0000-0003-0832-116X (author list not supplied) |
| Observed identifiers | doi=10.14778/3538598.3538615 (self); issn=2150-8097 (part-of) | doi=10.14778/3538598.3538615 (self); wosuid=WOS:000992384400018 (self) |

_helper: normalized DOI A=['10.14778/3538598.3538615'] B=['10.14778/3538598.3538615'] -> equal_

**AI-proposed label: `same`**

**Note:** ORCID activities from records 0000-0001-7793-9049 and 0000-0003-0832-116X both carry DOI 10.14778/3538598.3538615, the title "CORE: a complex event recognition engine" (capitalization differs) and publicationYear 2022.

**Supporting evidence:**
- Normalized observedDoi equal
- Title identical apart from capitalization
- Same year 2022

**Conflicting evidence:**
- Different ORCID record owners (consistent with co-authors)

**Limitations / missing information:**
- No author list or pages

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:aa86eeceb24fd9d5376b1376ab6a92317241a090bf92841c61a9912df71421b2` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:214`
- B `orcid-activity` `er-evidence:7a81970ba2e5976a88a23542e564a77668fcb369f2e2094b9eb8ea5897a176f2` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:306`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 226 — Work

- **pairId:** `resolution-pair:167065dd7daeadca3ae6368389e1d06ba4805de8e6e7d3b664a785a4155f47c2`
- **evidenceHash:** `ad17198404fd15dc5eff6f4b28751128566b18232a12d9cf75926ca81f441e8b`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3174659798 (article) | OPENALEX W4281972940 (conference-paper) |
| Title | Rearchitecting Linux Storage Stack for µs Latency and High Throughput | DB-BERT: A Database Tuning Tool that "Reads the Manual" |
| Year | 2021 | 2022 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4393915683 |
| DOI | — | 10.1145/3514221.3517843 |
| arXiv ID | — | — |
| Pages | 113-128 | 190-203 |
| Authors | (4) Jaehyun Hwang, Midhul Vuppalapati, Simon Peter, Rachit Agarwal | (1) Immanuel Trummer |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3514221.3517843, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3514221.3517843, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.1145/3514221.3517843'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Rearchitecting Linux Storage Stack for µs Latency and High Throughput" (no DOI, OSDI 2021) and B "DB-BERT: A Database Tuning Tool that 'Reads the Manual'" (10.1145/3514221.3517843, 2022) have unrelated titles and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2021 vs 2022
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:18cd80b4a21c60deca8ffe5dcc8f34ca0ea968bdbe9ce4869391b7f37eae18a3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:205`
- B `work` `er-evidence:92eec0ac96307fdee94effce8ceccfdd30d9b75ca0bc5c99381be2fbceccdd30` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:149`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 227 — Work

- **pairId:** `resolution-pair:94672d1e2cf27c091440bde0c24aed2dd87cf1ef7f0520c09a0c2b537d303bd7`
- **evidenceHash:** `24b34af60508903042be85eb5ebaf6a654401bb5821328d4d25ba2b25712bb64`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-1547-2847/work/113367184 | OPENALEX W3117066972 (article) |
| Title | LF-GDPR: A Framework for Estimating Graph Metrics with Local Differential Privacy | LF-GDPR: A Framework for Estimating Graph Metrics With Local Differential Privacy |
| Year | publicationYear=2022 | 2020 |
| Venue ID | — | venue:openalex:S30698027 |
| DOI | 10.1109/tkde.2020.3047124 | 10.1109/tkde.2020.3047124 |
| arXiv ID | — | — |
| Pages | — | 4905-4920 |
| Authors | ORCID record owner 0000-0003-1547-2847 (author list not supplied) | (5) Qingqing Ye, Haibo Hu, Man Ho Au, Xiaofeng Meng, Xiaokui Xiao |
| Observed identifiers | doi=10.1109/tkde.2020.3047124 (self) | namespace=openalex.doi, value=https://doi.org/10.1109/tkde.2020.3047124, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/tkde.2020.3047124, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1109/tkde.2020.3047124'] B=['10.1109/tkde.2020.3047124'] -> equal_

**AI-proposed label: `same`**

**Note:** ORCID activity 0000-0003-1547-2847/work/113367184 and the OpenAlex work W3117066972 share DOI 10.1109/tkde.2020.3047124 and the title "LF-GDPR: A Framework for Estimating Graph Metrics with/With Local Differential Privacy".

**Supporting evidence:**
- Normalized DOI equal
- Title identical apart from capitalization

**Conflicting evidence:**
- Year 2022 (ORCID publicationYear) vs 2020 (OpenAlex) — consistent with online-first vs issue date

**Limitations / missing information:**
- ORCID activity has no author list

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:c4cb7f28d44b4129802feb48db56c0bfd67a73194ed6d0ad4c0cc1e62c29a79f` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:234`
- B `work` `er-evidence:2926dba60f619ca24083ff8742e10e6e02f0fc994c2da768c37fb1503ad8e5f5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:223`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 228 — Work

- **pairId:** `resolution-pair:4ec4d96f36a39d44f8561f8dca8463060fb1e71cca639b79cab52fd4bc8c7682`
- **evidenceHash:** `0dc46e780e790b444a1e8402c6845dc96e731416a6193e12fd51519e36f0c93e`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-1547-2847/work/113367147 | ORCID activity 0000-0003-1547-2847/work/120650965 |
| Title | SPMAC: Scalable Prefix Verifiable Message Authentication Code for Internet of Things | SPMAC: Scalable Prefix Verifiable Message Authentication Code for Internet of Things |
| Year | publicationYear=2022 | publicationYear=2022 |
| Venue ID | — | — |
| DOI | 10.1109/tnsm.2022.3169657 | 10.1109/tnsm.2022.3169657 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0003-1547-2847 (author list not supplied) | ORCID record owner 0000-0003-1547-2847 (author list not supplied) |
| Observed identifiers | doi=10.1109/tnsm.2022.3169657 (self) | doi=10.1109/TNSM.2022.3169657 (self) |

_helper: normalized DOI A=['10.1109/tnsm.2022.3169657'] B=['10.1109/tnsm.2022.3169657'] -> equal_

**AI-proposed label: `same`**

**Note:** Two activities on ORCID record 0000-0003-1547-2847 carry DOI 10.1109/tnsm.2022.3169657, the identical title "SPMAC: Scalable Prefix Verifiable Message Authentication Code for Internet of Things" and publicationYear 2022.

**Supporting evidence:**
- Normalized observedDoi equal
- Identical title
- Same year and ORCID record owner

**Conflicting evidence:**
- Distinct activity ids (duplicate entries)

**Limitations / missing information:**
- No author list or pages

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:86afc5d6a13a578fc911a9f28aac3487fc637092fb8349ccca2c2fdb5cfd7c4b` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:227`
- B `orcid-activity` `er-evidence:c87460f7e8198cbb21aec864a6ada1058f4e9d0cddb538a5313e7cc340c44417` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:238`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 229 — Work

- **pairId:** `resolution-pair:1f929d8f5a7a732de747946bc944c4b1b783ab73625d17b80e5e06917528469e`
- **evidenceHash:** `cfaf5a50d8930bf21f695a30e45af20c561729a52af1ed5fa738e87aaf5fbaa9`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-1547-2847/work/118874719 | OPENALEX W3117066972 (article) |
| Title | LF-GDPR: A Framework for Estimating Graph Metrics With Local Differential Privacy | LF-GDPR: A Framework for Estimating Graph Metrics With Local Differential Privacy |
| Year | publicationYear=2022 | 2020 |
| Venue ID | — | venue:openalex:S30698027 |
| DOI | 10.1109/tkde.2020.3047124 | 10.1109/tkde.2020.3047124 |
| arXiv ID | — | — |
| Pages | — | 4905-4920 |
| Authors | ORCID record owner 0000-0003-1547-2847 (author list not supplied) | (5) Qingqing Ye, Haibo Hu, Man Ho Au, Xiaofeng Meng, Xiaokui Xiao |
| Observed identifiers | doi=10.1109/TKDE.2020.3047124 (self) | namespace=openalex.doi, value=https://doi.org/10.1109/tkde.2020.3047124, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/tkde.2020.3047124, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1109/tkde.2020.3047124'] B=['10.1109/tkde.2020.3047124'] -> equal_

**AI-proposed label: `same`**

**Note:** ORCID activity 0000-0003-1547-2847/work/118874719 and OpenAlex work W3117066972 share DOI 10.1109/tkde.2020.3047124 and the identical title "LF-GDPR: A Framework for Estimating Graph Metrics With Local Differential Privacy".

**Supporting evidence:**
- Normalized DOI equal
- Identical title

**Conflicting evidence:**
- Year 2022 (ORCID) vs 2020 (OpenAlex) — consistent with online-first vs issue date

**Limitations / missing information:**
- ORCID activity has no author list

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:fcf3a8e1ee9060700fd485a33124d5151d60a28623c2cb702cc9f0fb3e91f977` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:236`
- B `work` `er-evidence:2926dba60f619ca24083ff8742e10e6e02f0fc994c2da768c37fb1503ad8e5f5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:223`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 230 — Researcher

- **pairId:** `resolution-pair:0be9d36df2f219d22d6b9dfd8803a7d217ac8fa4ca93228d843cf63e04fce3d1`
- **evidenceHash:** `871820d8648d78073954063eb5c8ad873f544fa5d0c73949291217a11e373126`
- **Question:** do mention A `mention:crossref:10.1145/3299887.3299889#1` and B `mention:openalex:W2904324473#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:crossref:10.1145/3299887.3299889#1 | mention:openalex:W2904324473#1 |
| Name as written | Michael Benedikt | Michael Benedikt |
| Author position | 1 of 1 | 1 of 1 |
| ORCID on mention | — | 0000-0003-2964-0880 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5037774973 |
| Affiliation | "University of Oxford, Queensland, United Kingdom" | ROR 052gg0110 |
| Work title | Logic-based Perspectives on Query Reformulationover Restricted Interfaces | Logic-based Perspectives on Query Reformulationover Restricted Interfaces |
| Year | 2018 | 2018 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S47508943 |
| DOI | 10.1145/3299887.3299889 | 10.1145/3299887.3299889 |
| Coauthors | — | — |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=- B=['052gg0110'] shared=none_

**AI-proposed label: `same`**

**Note:** Both mentions are the sole author "Michael Benedikt" of the same publication: Crossref and OpenAlex records of DOI 10.1145/3299887.3299889 ("Logic-based Perspectives on Query Reformulation over Restricted Interfaces", 2018, pages 5-16).

**Supporting evidence:**
- Both mentions are author#1 of a single-author work
- The two works share normalized DOI 10.1145/3299887.3299889, title, year and pages
- Cross-source: A from CROSSREF, B from OPENALEX

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- Affiliation forms not comparable: A organizationName "University of Oxford, Queensland, United Kingdom" vs B ROR 052gg0110
- B observedOrcid is OpenAlex-supplied only

<details><summary>Evidence references</summary>

- A `mention-affiliation` `er-evidence:1547c45c2b9a066530d94f82563e8f2909c2841449e6b61f9d5bb2c33a603d17` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/mention-affiliation/part-r-00000:35`
- A `work` `er-evidence:9a525f2d788aa1d202be967926aee60c9e9c0ed6c1feb44d1825541a4606fd27` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:7`
- B `work` `er-evidence:0ef77317d84c100171fe86ce78fa7976f99ec20778a7f3a6a1fcba9f488110ab` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:370`
- B `enrichment` `er-evidence:8b39532294c98ed2f7dc215f83ada1247b78556efd92331c044db0cbed8a1dae` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3845`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 231 — Work

- **pairId:** `resolution-pair:eddc3bb79f6b9198ed3b9ac9dce7bdeb8b24efe2dda12ae40f485c0ce1a9fcd8`
- **evidenceHash:** `9c2fcdde72af5a9ac9c4fd9ceab12b42f88af4e0b964996be7e5af5585241d12`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-1547-2847/work/112998839 | ORCID activity 0000-0003-1547-2847/work/69215081 |
| Title | Local Differential Privacy: Tools, Challenges, and Opportunities | Local Differential Privacy: Tools, Challenges, and Opportunities |
| Year | publicationYear=2019 | publicationYear=2020 |
| Venue ID | — | — |
| DOI | 10.1007/978-981-15-3281-8_2 | 10.1007/978-981-15-3281-8_2 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0003-1547-2847 (author list not supplied) | ORCID record owner 0000-0003-1547-2847 (author list not supplied) |
| Observed identifiers | doi=10.1007/978-981-15-3281-8_2 (self) | doi=10.1007/978-981-15-3281-8_2 (self) |

_helper: normalized DOI A=['10.1007/978-981-15-3281-8_2'] B=['10.1007/978-981-15-3281-8_2'] -> equal_

**AI-proposed label: `same`**

**Note:** Two activities on ORCID record 0000-0003-1547-2847 carry DOI 10.1007/978-981-15-3281-8_2 and the identical title "Local Differential Privacy: Tools, Challenges, and Opportunities".

**Supporting evidence:**
- Normalized observedDoi equal
- Identical title
- Same ORCID record owner

**Conflicting evidence:**
- publicationYear 2019 vs 2020 (consistent with online vs print date)

**Limitations / missing information:**
- No author list or pages

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:2512e10c0c39fed67b70610883cc7e752be8018f4844d4e225b22ca9fe264819` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:226`
- B `orcid-activity` `er-evidence:f633eea85c3380477d584c3e3c82b5ca9896310bf971018c30d94ffd2dfcc58a` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:259`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 232 — Researcher

- **pairId:** `resolution-pair:ced94ab330ec16c10d0414b1fe25fa899e65d0ae0180fb15970251d09b0e8783`
- **evidenceHash:** `6011ce3339331515b03ddf4a44fd44386644b637b76f41a509ba1179967b2b5e`
- **Question:** do mention A `mention:crossref:10.1145/3299887.3299889#1` and B `mention:openalex:W4311994618#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:crossref:10.1145/3299887.3299889#1 | mention:openalex:W4311994618#1 |
| Name as written | Michael Benedikt | Michael Benedikt |
| Author position | 1 of 1 | 1 of 5 |
| ORCID on mention | — | 0000-0003-2964-0880 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5037774973 |
| Affiliation | "University of Oxford, Queensland, United Kingdom" | ROR 052gg0110 |
| Work title | Logic-based Perspectives on Query Reformulationover Restricted Interfaces | Rewriting the infinite chase |
| Year | 2018 | 2022 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S4210226185 |
| DOI | 10.1145/3299887.3299889 | 10.14778/3551793.3551851 |
| Coauthors | — | Maxime Buron, Stefano Germano, Kevin Kappelmann, Boris Motik |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=- B=['052gg0110'] shared=none_

**AI-proposed label: `uncertain`**

**Note:** A is Crossref sole author "Michael Benedikt" (organizationName "University of Oxford, Queensland, United Kingdom") on a 2018 query-reformulation survey; B is "Michael Benedikt" (ROR 052gg0110) on "Rewriting the infinite chase" (2022). The name and related topic match, but the affiliation forms cannot be compared and no coauthor is shared.

**Supporting evidence:**
- Name exact match: author#1 in both
- Related topic: logic-based query reformulation/rewriting

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- Affiliation string vs ROR id without a name cannot be compared
- A has no identifiers; B observedOrcid is OpenAlex-supplied only
- Leans same

<details><summary>Evidence references</summary>

- A `mention-affiliation` `er-evidence:1547c45c2b9a066530d94f82563e8f2909c2841449e6b61f9d5bb2c33a603d17` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/mention-affiliation/part-r-00000:35`
- A `work` `er-evidence:9a525f2d788aa1d202be967926aee60c9e9c0ed6c1feb44d1825541a4606fd27` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:7`
- B `enrichment` `er-evidence:680578fdfa824647cb23600d4fbb8e2e26e679e6bc29906a8c018be7305e8fce` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1362`
- B `work` `er-evidence:d5e2eaaadb905d03baa7c676f0ae505d544cb44b645f4f0ba7af46badd1985df` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:126`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Semantic Scholar assigns the same author ID on both papers (api.semanticscholar.org).

---

## Task 233 — Researcher

- **pairId:** `resolution-pair:8bc2f23f58b2bdb5435daeb2d7ebea53007a311383b6e53559fa630c9d2065dc`
- **evidenceHash:** `a27188c9c005e029820be00c32cec1cbeeeb89ead323c6aa816f8d3c396fe150`
- **Question:** do mention A `mention:openalex:W3043413334#2` and B `mention:openalex:W4289401659#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3043413334#2 | mention:openalex:W4289401659#4 |
| Name as written | Amar Phanishayee | Amar Phanishayee |
| Author position | 2 of 4 | 4 of 5 |
| ORCID on mention | 0009-0001-2777-1118 (OpenAlex-supplied) | 0009-0001-2777-1118 (OpenAlex-supplied) |
| OpenAlex author ID | A5011102459 | A5011102459 |
| Affiliation | ROR 00d0nc645 | ROR 00d0nc645 |
| Work title | Analyzing and mitigating data stalls in DNN training | Parameter Hub |
| Year | 2021 | 2018 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S7407088165 |
| DOI | 10.14778/3446095.3446100 | 10.1145/3267809.3267840 |
| Coauthors | Jayashree Mohan, Ashish Raniwala, Vijay Chidambaram | Liang Luo, Jacob Nelson, Luis Ceze, Arvind Krishnamurthy |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00d0nc645'] B=['00d0nc645'] shared=['00d0nc645']_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Amar Phanishayee" with ROR 00d0nc645, but no coauthor is shared between "Analyzing and mitigating data stalls in DNN training" (2021) and "Parameter Hub" (2018), whose truncated title gives little topic signal.

**Supporting evidence:**
- Name exact match: A author#2, B author#4
- enrichment ror=00d0nc645 on both target mentions
- Same OpenAlex-supplied observedOrcid 0009-0001-2777-1118 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- B title "Parameter Hub" too short to establish topic continuity
- Leans same given the distinctive name and shared ROR

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:58519dfcbbcb0f7a59a6b17bbb50ef58aa1c016dde8dbdd53e3d5a44c73fd310` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2875`
- A `work` `er-evidence:77b036bbd65889087be36687fc27df3b9c8f6d2a0000dd28f9ac08b86a2ca35d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:263`
- B `work` `er-evidence:8a49ae3edbf36b2af30fe7aead11d22955b5c937b9d0841df5a7b4d9f773a96b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:135`
- B `enrichment` `er-evidence:daa6dcad39bca6424d6c5b396e61ebdae2c4ef4ac34ed50776bcd464544a246f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1449`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Semantic Scholar assigns the same author ID on both papers (api.semanticscholar.org).

---

## Task 234 — Researcher

- **pairId:** `resolution-pair:792b2026d8aae47057430bef742ceb54eb69300ec4949df7c916eaf075c2d5c3`
- **evidenceHash:** `039c2e0e088ddc7600144fde027fe3d027f25bfcfdb63f719fb7ab83063c64ee`
- **Question:** do mention A `mention:openalex:W4321448364#1` and B `mention:openalex:W4389539730#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4321448364#1 | mention:openalex:W4389539730#4 |
| Name as written | Avanika Narayan | Avanika Narayan |
| Author position | 1 of 4 | 4 of 7 |
| ORCID on mention | — | — |
| OpenAlex author ID | A5039749428 | A5039749428 |
| Affiliation | ROR 00f54p054 | ROR 00f54p054 |
| Work title | Can Foundation Models Wrangle Your Data? | Language Models Enable Simple Systems for Generating Structured Views of Heterogeneous Data Lakes |
| Year | 2022 | 2023 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210226185 |
| DOI | 10.14778/3574245.3574258 | 10.14778/3626292.3626294 |
| Coauthors | Ines Chami, Laurel Orr, Christopher Ré | Simran Arora, Brandon Yang, Sabri Eyuboglu, Andrew Hojel, Immanuel Trummer, Christopher Ré |

_helper: shared coauthor normalizedNames = ['christopher ré']_
_helper: target-mention ROR A=['00f54p054'] B=['00f54p054'] shared=['00f54p054']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Avanika Narayan" with shared coauthor Christopher Ré, the same ROR 00f54p054, and foundation-model data-management topics ("Can Foundation Models Wrangle Your Data?" 2022; "Language Models Enable Simple Systems…" 2023).

**Supporting evidence:**
- Name exact match: A author#1, B author#4
- Shared coauthor in payload: Christopher Ré
- enrichment ror=00f54p054 on both target mentions
- Specific topic continuity
- Same OpenAlex author id A5039749428 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- No ORCID on either mention

<details><summary>Evidence references</summary>

- A `work` `er-evidence:5b00867f970a5bca6056c318e8e5eaf60e59901419bcf201a8af72e9e1c80b4e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:119`
- A `enrichment` `er-evidence:737dc7cbe6b0bec0d68f1c6de056afce80a3f160fbb2840898c537068ad188e4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1308`
- B `work` `er-evidence:b52af49df5e710c14d8349165a45d91793cb3fceb4b5312cc67eb17813b99805` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:55`
- B `enrichment` `er-evidence:bb3588a6611df516a11db6286b092cc2e5fce0b680b642309dd8410e645d85d2` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:611`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 235 — Researcher

- **pairId:** `resolution-pair:ef744ab8e9abe8335a1222f8188e829c70e607e2810a280ff17d6202875277ce`
- **evidenceHash:** `e6f7dc9b2f0f7f7be3692baab75446d43aab72dd5fb1f1bf4244c8716cfc0da4`
- **Question:** do mention A `mention:openalex:W2898855235#3` and B `mention:openalex:W2985432842#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2898855235#3 | mention:openalex:W2985432842#1 |
| Name as written | Jaehong Kim | Jeongchul Kim |
| Author position | 3 of 5 | 1 of 2 |
| ORCID on mention | 0000-0002-9111-9976 (OpenAlex-supplied) | 0000-0002-2369-4653 (OpenAlex-supplied) |
| OpenAlex author ID | A5101480473 | A5039039349 |
| Affiliation | — | ROR 0049erg63 |
| Work title | Neural adaptive content-aware internet video delivery | Practical Cloud Workloads for Serverless FaaS |
| Year | 2018 | 2019 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S7407088165 |
| DOI | 10.5555/3291168.3291216 | 10.1145/3357223.3365439 |
| Coauthors | Hyunho Yeo, Youngmok Jung, Jinwoo Shin, Dongsu Han | Kyungyong Lee |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=- B=['0049erg63'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#3 "Jaehong Kim" and B author#1 "Jeongchul Kim" have different given names; no coauthor overlap.

**Supporting evidence:**
- nameText given names differ: "Jaehong" vs "Jeongchul"
- No shared coauthors
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no affiliation evidence

<details><summary>Evidence references</summary>

- A `work` `er-evidence:03660c3d1b9014243e10e1e980605ff561010e989769fb879f8bfc69736d7660` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:382`
- B `enrichment` `er-evidence:e6406424f84ba83e229073bc93c67b4a99729df67a398eb57cbe52129409fadb` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3307`
- B `work` `er-evidence:f97815167f3bfef63bb17a3e1b81f1b3e7a274742b7178cae763040f23c03e41` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:313`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 236 — Work

- **pairId:** `resolution-pair:c552a485b80e43b1fa736d0762efe837b98007a0faf64de289d309fc3ae424cf`
- **evidenceHash:** `aa195291a23e6e50288c2d4037ba093a2bc3434300b26911192b381723ae7f83`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0002-6698-2735/work/132962091 | ORCID activity 0000-0002-6698-2735/work/60530724 |
| Title | Logics for Unranked Trees: An Overview | Logics for Unranked Trees: An Overview |
| Year | publicationYear=2006 | publicationYear=2006 |
| Venue ID | — | — |
| DOI | 10.2168/lmcs-2(3:2)2006 | 10.2168/lmcs-2(3:2)2006 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0002-6698-2735 (author list not supplied) | ORCID record owner 0000-0002-6698-2735 (author list not supplied) |
| Observed identifiers | doi=10.2168/LMCS-2(3:2)2006 (self) | source-work-id=19933431-6bbe-469f-a1e2-fc9a2c6a1c18 (self); eid=2-s2.0-33845385911 (self); doi=10.2168/LMCS-2(3:2)2006 (self) |

_helper: normalized DOI A=['10.2168/lmcs-2(3:2)2006'] B=['10.2168/lmcs-2(3:2)2006'] -> equal_

**AI-proposed label: `same`**

**Note:** Two activities on ORCID record 0000-0002-6698-2735 carry DOI 10.2168/lmcs-2(3:2)2006, the identical title "Logics for Unranked Trees: An Overview" and publicationYear 2006.

**Supporting evidence:**
- Normalized observedDoi equal
- Identical title
- Same year and ORCID record owner

**Conflicting evidence:**
- Distinct activity ids; B adds eid=2-s2.0-33845385911 and a source-work-id (duplicate entries)

**Limitations / missing information:**
- No author list or pages

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:459b698e9f76d8a61e0efa04762433b37dbaf135dfee83e2a7b162df7efe3e9c` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:3`
- B `orcid-activity` `er-evidence:3b23ff265a62a750b7d5f93f1acf0cea5532bec76e66b3dd7b2f26663ae4ff04` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:358`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 237 — Work

- **pairId:** `resolution-pair:c0ccd065f779894023167a1f225700754af922aed7899ca35ec4fd35e1d2c52b`
- **evidenceHash:** `d193541769a344810197094c5a905cb51bdf87b7a6f4a8cd902da3c3e4831f01`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-1547-2847/work/113367161 | ORCID activity 0000-0003-1547-2847/work/126485038 |
| Title | PrivKVM*: Revisiting Key-Value Statistics Estimation with Local Differential Privacy | PrivKVM*: Revisiting Key-Value Statistics Estimation With Local Differential Privacy |
| Year | publicationYear=2021 | publicationYear=2023 |
| Venue ID | — | — |
| DOI | 10.1109/tdsc.2021.3107512 | 10.1109/tdsc.2021.3107512 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0003-1547-2847 (author list not supplied) | ORCID record owner 0000-0003-1547-2847 (author list not supplied) |
| Observed identifiers | doi=10.1109/tdsc.2021.3107512 (self) | doi=10.1109/TDSC.2021.3107512 (self) |

_helper: normalized DOI A=['10.1109/tdsc.2021.3107512'] B=['10.1109/tdsc.2021.3107512'] -> equal_

**AI-proposed label: `same`**

**Note:** Two activities on ORCID record 0000-0003-1547-2847 carry DOI 10.1109/tdsc.2021.3107512 and the title "PrivKVM*: Revisiting Key-Value Statistics Estimation with/With Local Differential Privacy".

**Supporting evidence:**
- Normalized observedDoi equal
- Title identical apart from capitalization
- Same ORCID record owner

**Conflicting evidence:**
- publicationYear 2021 vs 2023 (consistent with online-first vs issue year)

**Limitations / missing information:**
- No author list or pages

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:01d32e70e7815f34cd9cbb9a8f51a665ed66a8b9e5719a5e940a11d2ff0cd157` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:230`
- B `orcid-activity` `er-evidence:47f777a14b8eb7eebbae77df26fd7b3293cef9e7e5ef9ba02f27dfb694ff621a` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:253`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 238 — Work

- **pairId:** `resolution-pair:78c24d80a14c24a20f18c0edb6e20298c9372942d15491687b417c4d9347421f`
- **evidenceHash:** `73d85617e8fdf2e2355896cf732d922156c0a32b6adb24f9eab00a0130a73dbd`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-0832-116X/work/151681321 | OPENALEX W2790867877 (conference-paper) |
| Title | Constant Delay Algorithms for Regular Document Spanners | Constant Delay Algorithms for Regular Document Spanners |
| Year | publicationYear=2018 | 2018 |
| Venue ID | — | venue:openalex:S7407087293 |
| DOI | 10.1145/3196959.3196987 | 10.1145/3196959.3196987 |
| arXiv ID | — | — |
| Pages | — | 165-177 |
| Authors | ORCID record owner 0000-0003-0832-116X (author list not supplied) | (5) Fernando Florenzano, Cristian Riveros, Martin Ugarte, Stijn Vansummeren, Domagoj Vrgoc |
| Observed identifiers | doi=10.1145/3196959.3196987 (self); wosuid=WOS:000455483100013 (self) | namespace=openalex.doi, value=https://doi.org/10.1145/3196959.3196987, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3196959.3196987, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3196959.3196987'] B=['10.1145/3196959.3196987'] -> equal_

**AI-proposed label: `same`**

**Note:** ORCID activity 0000-0003-0832-116X/work/151681321 and OpenAlex work W2790867877 share DOI 10.1145/3196959.3196987, the title "Constant Delay Algorithms for Regular Document Spanners" and year 2018.

**Supporting evidence:**
- Normalized DOI equal
- Identical title
- Year 2018 on both

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- ORCID activity has no author list

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:6ea31b6added941ade7b54464aa3c40520a988ce3ec43ddefcd9a40d2ba31829` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:294`
- B `work` `er-evidence:a3456d9611f41700ebb2ec6ce329192a0e2e91ccf89b1e94e50c1288ede5c242` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:439`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 239 — Researcher

- **pairId:** `resolution-pair:1347e30466549013b8c1bd84220f29cf0e89382be2322a64a72d79e6754a8d0d`
- **evidenceHash:** `03d982f3498d7b35ceb5ac9daf8b52d7852a880e5284c1539c4902cb49e8b0f5`
- **Question:** do mention A `mention:crossref:10.1145/3299887.3299889#1` and B `mention:openalex:W2659288104#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:crossref:10.1145/3299887.3299889#1 | mention:openalex:W2659288104#2 |
| Name as written | Michael Benedikt | Michael Benedikt |
| Author position | 1 of 1 | 2 of 2 |
| ORCID on mention | — | 0000-0003-2964-0880 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5037774973 |
| Affiliation | "University of Oxford, Queensland, United Kingdom" | ROR 052gg0110 |
| Work title | Logic-based Perspectives on Query Reformulationover Restricted Interfaces | When Can We Answer Queries Using Result-Bounded Data Interfaces? |
| Year | 2018 | 2018 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S7407087293 |
| DOI | 10.1145/3299887.3299889 | 10.1145/3196959.3196965 |
| Coauthors | — | Antoine Amarilli |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=- B=['052gg0110'] shared=none_

**AI-proposed label: `uncertain`**

**Note:** A is Crossref sole author "Michael Benedikt" (organizationName "University of Oxford, Queensland, United Kingdom") on "Logic-based Perspectives on Query Reformulation over Restricted Interfaces" (2018); B is "Michael Benedikt" (ROR 052gg0110) on "When Can We Answer Queries Using Result-Bounded Data Interfaces?" (2018). The topic match is specific, but affiliations are not comparable and no coauthor is shared.

**Supporting evidence:**
- Name exact match
- Specific topic continuity: queries over restricted/result-bounded interfaces
- Same year 2018

**Conflicting evidence:**
- No shared coauthors (A single-authored)

**Limitations / missing information:**
- Affiliation string vs ROR id without a name cannot be compared
- A has no identifiers; B observedOrcid is OpenAlex-supplied only
- Leans same

<details><summary>Evidence references</summary>

- A `mention-affiliation` `er-evidence:1547c45c2b9a066530d94f82563e8f2909c2841449e6b61f9d5bb2c33a603d17` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/mention-affiliation/part-r-00000:35`
- A `work` `er-evidence:9a525f2d788aa1d202be967926aee60c9e9c0ed6c1feb44d1825541a4606fd27` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:7`
- B `work` `er-evidence:46da9c0da019a9220596b8fc699e9c2e066bc33eabde9ba9561b57a9d0bb0bf0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:445`
- B `enrichment` `er-evidence:a6e9da00e5dd2d1bff1c6ca49c3d91c635b528f8b1e1c327f8fb232e03f5376e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4509`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Semantic Scholar assigns the same author ID on both papers (api.semanticscholar.org).

---

## Task 240 — Work

- **pairId:** `resolution-pair:774b465a227565a82409acfad3c6ab5c1c79e9e9a2c5fac4554dcf9a12a4c11b`
- **evidenceHash:** `762977e157a96a07b2a505544e1bd4508d677f097a921d3fb49f3e5b9f09d31c`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0002-6698-2735/work/132962094 | ORCID activity 0000-0002-6698-2735/work/60530704 |
| Title | Graph Logics with Rational Relations | Graph Logics with Rational Relations |
| Year | publicationYear=2013 | publicationYear=2013 |
| Venue ID | — | — |
| DOI | 10.2168/lmcs-9(3:1)2013 | 10.2168/lmcs-9(3:1)2013 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0002-6698-2735 (author list not supplied) | ORCID record owner 0000-0002-6698-2735 (author list not supplied) |
| Observed identifiers | doi=10.2168/LMCS-9(3:1)2013 (self) | source-work-id=03e1eef6-6884-43ae-8021-40cc7f7d94ef (self); eid=2-s2.0-84879961953 (self); doi=10.2168/LMCS-9(3:1)2013 (self) |

_helper: normalized DOI A=['10.2168/lmcs-9(3:1)2013'] B=['10.2168/lmcs-9(3:1)2013'] -> equal_

**AI-proposed label: `same`**

**Note:** Two activities on ORCID record 0000-0002-6698-2735 carry DOI 10.2168/lmcs-9(3:1)2013, the identical title "Graph Logics with Rational Relations" and publicationYear 2013.

**Supporting evidence:**
- Normalized observedDoi equal
- Identical title
- Same year and ORCID record owner

**Conflicting evidence:**
- Distinct activity ids; B adds eid=2-s2.0-84879961953 and a source-work-id (duplicate entries)

**Limitations / missing information:**
- No author list or pages

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:a5c834137c7b201b1d3b683afc8c1e45005065c71ae7d7efeb1665604ab07470` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:1`
- B `orcid-activity` `er-evidence:74a07d30efe435daa2ec959bc69d9971eefc2b5dfae026cb9dc8e14a007ce641` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:378`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

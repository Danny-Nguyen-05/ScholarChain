# ScholarChain AI review drafts — batch 10 (tasks 181–200)

> **Status: AI_SUGGESTIONS_PENDING_HUMAN_REVIEW.** These are AI-generated suggestions from a session-reported `claude-opus-5-5` model (not independently verified). They are not human reviews or gold labels. Record your own decision in each task's decision box; an empty box means not reviewed.

Queue: `review-queue:05c5817f62a70d378829be361b9c9169fc9af18448f7c83c245f1d65bbca6175`  
Work tasks: 16 · Researcher tasks: 4

Rows marked `>> … <<` in the raw data and the 'Name as written' row identify the mention being compared. OpenAlex author IDs and OpenAlex-supplied ORCIDs are provider hypotheses. Lines in _italics_ starting with 'helper:' are exact-string comparisons computed by a script to help reading; they are not judgments.

---
## Task 181 — Work

- **pairId:** `resolution-pair:c975635a8ec3f45a97db513823630b4bfab8b5a319c790eb660c46e2595563e5`
- **evidenceHash:** `052e071aa08b60b72c53368a9e62d4c656eb9f96dc3646feb9ed81795d899e78`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3031232306 (conference-paper) | OPENALEX W3093150360 (conference-paper) |
| Title | Self-paced Ensemble for Highly Imbalanced Massive Data Classification | Wukong |
| Year | 2020 | 2020 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S7407088165 |
| DOI | 10.1109/icde48307.2020.00078 | 10.1145/3419111.3421286 |
| arXiv ID | — | — |
| Pages | 841-852 | 1-15 |
| Authors | (7) Zhining Liu, Wei Cao, Zhifeng Gao, Jiang Bian, Hechang Chen, Yi Chang, Tie-Yan Liu | (6) Benjamin Carver, Jingyuan Zhang, Ao Wang, Ali Anwar, Panruo Wu, Yue Cheng |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde48307.2020.00078, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde48307.2020.00078, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3419111.3421286, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3419111.3421286, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1109/icde48307.2020.00078'] B=['10.1145/3419111.3421286'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Self-paced Ensemble for Highly Imbalanced Massive Data Classification" (10.1109/icde48307.2020.00078) and B "Wukong" (10.1145/3419111.3421286) are both 2020 but have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- venueId S4210210321 vs S7407088165
- work.authors disjoint

**Conflicting evidence:**
- Same year 2020

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:a13f1a83ae0eb7d63c89e205ca9c28403c945f5c5b452d523a3bb8883f749186` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:270`
- B `work` `er-evidence:6c77b692abc917bba0450a486a0c8f4c190577093c28451fbc94494874b6b18a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:253`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 182 — Researcher

- **pairId:** `resolution-pair:ebf91b3d605d8e7e7322b704a21d2db61f634128747dc624829bf908572a118c`
- **evidenceHash:** `52c010310aedbe90060fa80c24d7dbc34e4e47af310c471121fe0e27919bd8b1`
- **Question:** do mention A `mention:openalex:W3128793550#4` and B `mention:openalex:W4387321084#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3128793550#4 | mention:openalex:W4387321084#4 |
| Name as written | Yuxiang Wang | Yang Wang |
| Author position | 4 of 4 | 4 of 6 |
| ORCID on mention | 0000-0003-3240-2912 (OpenAlex-supplied) | 0000-0002-9721-4923 (OpenAlex-supplied) |
| OpenAlex author ID | A5100394398 | A5100322850 |
| Affiliation | ROR 0576gt767 | ROR 00rs6vg23 |
| Work title | A comprehensive survey and experimental comparison of graph-based approximate nearest neighbor search | Understanding Silent Data Corruptions in a Large Production CPU Population |
| Year | 2021 | 2023 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4306420989 |
| DOI | 10.14778/3476249.3476255 | 10.1145/3600006.3613149 |
| Coauthors | Mengzhao Wang, Xiaoliang Xu, Qiang Yue | Shaobu Wang, Guangyan Zhang, Junyu Wei, Jiesheng Wu, Qingchao Luo |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['0576gt767'] B=['00rs6vg23'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#4 "Yuxiang Wang" and B author#4 "Yang Wang" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Yuxiang" vs "Yang"
- No shared coauthors
- enrichment ror differs: 0576gt767 vs 00rs6vg23
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:40672fb5014082ff5772844d805e3dc53e79b18a113d69592ac7f27bbae479d4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:222`
- A `enrichment` `er-evidence:7b3d43708479dfb0052b333590592ee09f19f857963d1183ffe7cc1ea6e2525f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2426`
- B `work` `er-evidence:329a9a8a733b5b219e36963afeea58dbd45476bf4c0d6292dfbcca66479c3447` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:75`
- B `enrichment` `er-evidence:68f0afe48d790c6ccc8c5eca35c48b57048523a2f185cde5ebd23185b40751a8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:826`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 183 — Work

- **pairId:** `resolution-pair:28945293206d087cfeced13811cb2a998d358dbd88c42aa2fbcaea070cd17caa`
- **evidenceHash:** `689fd43c615e62d6001eee2e3486a19a325b29826e6b765c658aba1e5a3bf77f`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-1547-2847/work/113367184 | ORCID activity 0000-0003-1547-2847/work/118874719 |
| Title | LF-GDPR: A Framework for Estimating Graph Metrics with Local Differential Privacy | LF-GDPR: A Framework for Estimating Graph Metrics With Local Differential Privacy |
| Year | publicationYear=2022 | publicationYear=2022 |
| Venue ID | — | — |
| DOI | 10.1109/tkde.2020.3047124 | 10.1109/tkde.2020.3047124 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0003-1547-2847 (author list not supplied) | ORCID record owner 0000-0003-1547-2847 (author list not supplied) |
| Observed identifiers | doi=10.1109/tkde.2020.3047124 (self) | doi=10.1109/TKDE.2020.3047124 (self) |

_helper: normalized DOI A=['10.1109/tkde.2020.3047124'] B=['10.1109/tkde.2020.3047124'] -> equal_

**AI-proposed label: `same`**

**Note:** Two activities on ORCID record 0000-0003-1547-2847 carry the same DOI 10.1109/tkde.2020.3047124 (case differs only), the same title "LF-GDPR: A Framework for Estimating Graph Metrics with/With Local Differential Privacy" and publicationYear 2022.

**Supporting evidence:**
- Normalized observedDoi equal: 10.1109/tkde.2020.3047124
- orcid-activity.title identical apart from capitalization of 'with'
- publicationYear 2022 on both
- Same ORCID record owner

**Conflicting evidence:**
- Distinct ORCID activity ids (…/work/113367184 vs …/work/118874719) — duplicate entries on one profile

**Limitations / missing information:**
- No author list, venue or pages in ORCID activities

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:c4cb7f28d44b4129802feb48db56c0bfd67a73194ed6d0ad4c0cc1e62c29a79f` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:234`
- B `orcid-activity` `er-evidence:fcf3a8e1ee9060700fd485a33124d5151d60a28623c2cb702cc9f0fb3e91f977` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:236`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 184 — Work

- **pairId:** `resolution-pair:d3dee846277a7e5f5731e99cb5757db1683a0f4f429a04e9593e33ded94676f4`
- **evidenceHash:** `b8ce7e8c9a34477d0e324e1d2cd9b22fcb8fd214bfd38df30af8b09e12295d53`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | CROSSREF 10.1145/3299887.3299900 (journal-article) | OPENALEX W2905339588 (article) |
| Title | DANTE | DANTE |
| Year | 2018 | 2018 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S47508943 |
| DOI | 10.1145/3299887.3299900 | 10.1145/3299887.3299900 |
| arXiv ID | — | — |
| Pages | 67-72 | 67-72 |
| Authors | (2) Sourav S. Bhowmick, Xiaokui Xiaokui Xiao | (2) Sourav S. Bhowmick, Xiaokui Xiaokui Xiao |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3299887.3299900, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3299887.3299900, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3299887.3299900'] B=['10.1145/3299887.3299900'] -> equal_

**AI-proposed label: `same`**

**Note:** Crossref and OpenAlex records share DOI 10.1145/3299887.3299900, title "DANTE", year 2018, pages 67-72 and the identical two-author list (Sourav S. Bhowmick; Xiaokui Xiaokui Xiao).

**Supporting evidence:**
- Normalized DOI equal: 10.1145/3299887.3299900
- Identical title, year, pages and author list
- Venue consistent: Crossref issn 0163-5808 vs OpenAlex S47508943 (both journal records)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- Both records repeat the same irregular author string, so author agreement is partly copied metadata

<details><summary>Evidence references</summary>

- A `work` `er-evidence:690d131b6af699b1f16bff88ab11c81b14fbd5b45d538e17840e146128ff4308` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:10`
- B `work` `er-evidence:f07879e7bd66c3f62739682d6a6f67843f1223656b8e33974faba487b5d57605` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:367`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 185 — Work

- **pairId:** `resolution-pair:d9fa5bef296d4a0dae76c0ce95153542bb6c72cff503075b9f8a0fa59bcf414f`
- **evidenceHash:** `b99cb7d889df462c578e4b29978bc0e09716eca041077d14add213db782c05e1`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2911424454 (article) | OPENALEX W4321448364 (article) |
| Title | Snuba | Can Foundation Models Wrangle Your Data? |
| Year | 2018 | 2022 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210226185 |
| DOI | 10.14778/3291264.3291268 | 10.14778/3574245.3574258 |
| arXiv ID | — | — |
| Pages | 223-236 | 738-746 |
| Authors | (2) Paroma Varma, Christopher Ré | (4) Avanika Narayan, Ines Chami, Laurel Orr, Christopher Ré |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3291264.3291268, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3291264.3291268, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.14778/3574245.3574258, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3574245.3574258, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.14778/3291264.3291268'] B=['10.14778/3574245.3574258'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Snuba" (10.14778/3291264.3291268, 2018) and B "Can Foundation Models Wrangle Your Data?" (10.14778/3574245.3574258, 2022) have distinct DOIs and different titles; only Christopher Ré is shared.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2018 vs 2022; pages 223-236 vs 738-746

**Conflicting evidence:**
- Shared author Christopher Ré; same venueId S4210226185

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:dd8bd71aa52bb73ee830df4366b32cb6b0c6f8874cf6971905c038bc3dc9fe81` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:365`
- B `work` `er-evidence:5b00867f970a5bca6056c318e8e5eaf60e59901419bcf201a8af72e9e1c80b4e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:119`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 186 — Work

- **pairId:** `resolution-pair:df4425944ec0f7abcbd3739bb1c95dd941a8aad97d5db932acd9a7c57ad793dd`
- **evidenceHash:** `9e279834f0a006b6e47e3e8893b3bcb8b5a724c1df7940a5a1e761b9b50793f5`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-0832-116X/work/151681321 | CROSSREF 10.1145/3196959.3196987 (proceedings-article) |
| Title | Constant Delay Algorithms for Regular Document Spanners | Constant Delay Algorithms for Regular Document Spanners |
| Year | publicationYear=2018 | 2018 |
| Venue ID | — | None |
| DOI | 10.1145/3196959.3196987 | 10.1145/3196959.3196987 |
| arXiv ID | — | — |
| Pages | — | 165-177 |
| Authors | ORCID record owner 0000-0003-0832-116X (author list not supplied) | (5) Fernando Florenzano, Cristian Riveros, Martin Ugarte, Stijn Vansummeren, Domagoj Vrgoc |
| Observed identifiers | doi=10.1145/3196959.3196987 (self); wosuid=WOS:000455483100013 (self) | — |

_helper: normalized DOI A=['10.1145/3196959.3196987'] B=['10.1145/3196959.3196987'] -> equal_

**AI-proposed label: `same`**

**Note:** ORCID activity 0000-0003-0832-116X/work/151681321 has observedDoi 10.1145/3196959.3196987 and title "Constant Delay Algorithms for Regular Document Spanners" (2018), exactly matching the Crossref record for that DOI.

**Supporting evidence:**
- Normalized DOI equal: 10.1145/3196959.3196987
- Title identical
- Year 2018 on both

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- ORCID activity has no author list or pages for comparison

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:6ea31b6added941ade7b54464aa3c40520a988ce3ec43ddefcd9a40d2ba31829` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:294`
- B `work` `er-evidence:4f6776ddaca408a49641068a430f58a43e972bdb49a4b8b32b39bc711f0d3f47` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:3`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 187 — Work

- **pairId:** `resolution-pair:7bf7c98b116de4d3033b0c097528a0df9664b5ed158cbd0b0ac4f1893e047d5b`
- **evidenceHash:** `89fcff0cd174cb6baf5bb417e95f1424b5549eab05c8700411436015de509952`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-1547-2847/work/113367167 | ORCID activity 0000-0003-1547-2847/work/136454178 |
| Title | ReFlat: A Robust Access Pattern Hiding Solution for General Cloud Query Processing Based on K-isomorphism and Hardware Enclave | ReFlat: A Robust Access Pattern Hiding Solution for General Cloud Query Processing Based on K-Isomorphism and Hardware Enclave |
| Year | publicationYear=2021 | publicationYear=2023 |
| Venue ID | — | — |
| DOI | 10.1109/tcc.2021.3137351 | 10.1109/tcc.2021.3137351 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0003-1547-2847 (author list not supplied) | ORCID record owner 0000-0003-1547-2847 (author list not supplied) |
| Observed identifiers | doi=10.1109/tcc.2021.3137351 (self) | doi=10.1109/TCC.2021.3137351 (self) |

_helper: normalized DOI A=['10.1109/tcc.2021.3137351'] B=['10.1109/tcc.2021.3137351'] -> equal_

**AI-proposed label: `same`**

**Note:** Both activities on ORCID record 0000-0003-1547-2847 carry DOI 10.1109/tcc.2021.3137351 and the title "ReFlat: A Robust Access Pattern Hiding Solution for General Cloud Query Processing Based on K-isomorphism/K-Isomorphism and Hardware Enclave".

**Supporting evidence:**
- Normalized observedDoi equal: 10.1109/tcc.2021.3137351
- Title identical apart from capitalization
- Same ORCID record owner

**Conflicting evidence:**
- publicationYear 2021 vs 2023 (consistent with online-first vs issue year)

**Limitations / missing information:**
- No author list, venue or pages in ORCID activities

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:0ea73dfd1a84f0e99acfdf0d398b278ad9c0227dc86ac89d8f2fc171b140fe32` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:231`
- B `orcid-activity` `er-evidence:b5fb8f66855addcaaadf7397d2fcb93f52b2d98ba52f03820f901df2836672cc` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:256`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 188 — Work

- **pairId:** `resolution-pair:06e5ea29137c7b2af7ef1ae977d20e02c7d2d07e2a83b9e0aafe199736a658b6`
- **evidenceHash:** `7ab0c3a6c49e6eb3760ec1a0a06ed7a3e4766fd9fad3648eb2a79fe503ee92b7`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | CROSSREF 10.1145/3299887.3299889 (journal-article) | OPENALEX W2659288104 (conference-paper) |
| Title | Logic-based Perspectives on Query Reformulationover Restricted Interfaces | When Can We Answer Queries Using Result-Bounded Data Interfaces? |
| Year | 2018 | 2018 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S7407087293 |
| DOI | 10.1145/3299887.3299889 | 10.1145/3196959.3196965 |
| arXiv ID | — | — |
| Pages | 5-16 | 281-293 |
| Authors | (1) Michael Benedikt | (2) Antoine Amarilli, Michael Benedikt |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3196959.3196965, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3196959.3196965, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3299887.3299889'] B=['10.1145/3196959.3196965'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Logic-based Perspectives on Query Reformulation over Restricted Interfaces" (Crossref, 10.1145/3299887.3299889, SIGMOD Record, sole author Michael Benedikt) and B "When Can We Answer Queries Using Result-Bounded Data Interfaces?" (10.1145/3196959.3196965, PODS-type venue, Amarilli & Benedikt) have distinct DOIs and different titles.

**Supporting evidence:**
- work.doi distinct
- work.title different
- Author lists differ (1 vs 2 authors)
- Venue differs: issn 0163-5808 vs S7407087293; pages 5-16 vs 281-293

**Conflicting evidence:**
- Same year 2018; shared author Michael Benedikt; related topic (queries over restricted interfaces)

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:9a525f2d788aa1d202be967926aee60c9e9c0ed6c1feb44d1825541a4606fd27` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:7`
- B `work` `er-evidence:46da9c0da019a9220596b8fc699e9c2e066bc33eabde9ba9561b57a9d0bb0bf0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:445`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 189 — Work

- **pairId:** `resolution-pair:b88d9da4d5f85ae79a63ffe592d66c638f9351456d593d3b7ab75e1a77b125fb`
- **evidenceHash:** `af1c6a7f7f617a8d0b399dada1e8091980358af2c014e050b6d6b0521484ae14`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | CROSSREF 10.1145/3186549.3186561 (journal-article) | OPENALEX W4255125598 (article) |
| Title | Report from the Fourth Workshop on Algorithms andSystems for MapReduce and Beyond (BeyondMR '17) | Report from the Fourth Workshop on Algorithms andSystems for MapReduce and Beyond (BeyondMR '17) |
| Year | 2018 | 2018 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S47508943 |
| DOI | 10.1145/3186549.3186561 | 10.1145/3186549.3186561 |
| arXiv ID | — | — |
| Pages | 44-48 | 44-48 |
| Authors | (5) Foto N. Afrati, Jan Hidders, Paraschos Koutris, Jacek Sroka, Jeffrey Ullman | (5) Foto N. Afrati, Jan Hidders, Paraschos Koutris, Jacek Sroka, Jeffrey Ullman |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3186549.3186561, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3186549.3186561, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3186549.3186561'] B=['10.1145/3186549.3186561'] -> equal_

**AI-proposed label: `same`**

**Note:** Crossref and OpenAlex records share DOI 10.1145/3186549.3186561, the title "Report from the Fourth Workshop on Algorithms and Systems for MapReduce and Beyond (BeyondMR '17)", year 2018, pages 44-48 and the same five authors in order.

**Supporting evidence:**
- Normalized DOI equal
- Identical title, year, pages and five-author list (Foto N. Afrati, Jan Hidders, Paraschos Koutris, Jacek Sroka, Jeffrey Ullman)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:21bd3120640498611a5041137426de2a3fbfb380c6543e0002b3b74262dc8e80` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:2`
- B `work` `er-evidence:1502d7aa01c9a8dd6214bc580f52fbc2cb1a794b53839c3b9cb345614fc787d0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:156`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 190 — Researcher

- **pairId:** `resolution-pair:57c406e4a2c68b634aeb996d8858b70779b72ff80205f64983fbc148ce08ae17`
- **evidenceHash:** `35fcf72023985183d240e3117858bde6c439ea1ed93c2cf8b7d16446995796c1`
- **Question:** do mention A `mention:openalex:W3031232306#6` and B `mention:openalex:W4386591590#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3031232306#6 | mention:openalex:W4386591590#1 |
| Name as written | Yi Chang | Yanchuan Chang |
| Author position | 6 of 7 | 1 of 4 |
| ORCID on mention | — | 0000-0002-1376-0311 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5068430693 |
| Affiliation | ROR 00js3aw79 | ROR 01ej9dk98 |
| Work title | Self-paced Ensemble for Highly Imbalanced Massive Data Classification | Contrastive Trajectory Similarity Learning with Dual-Feature Attention |
| Year | 2020 | 2023 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210210321 |
| DOI | 10.1109/icde48307.2020.00078 | 10.1109/icde55515.2023.00224 |
| Coauthors | Zhining Liu, Wei Cao, Zhifeng Gao, Jiang Bian, Hechang Chen, Tie-Yan Liu | Jianzhong Qi, Yuxuan Liang, Egemen Tanin |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00js3aw79'] B=['01ej9dk98'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#6 "Yi Chang" and B author#1 "Yanchuan Chang" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Yi" vs "Yanchuan"
- No shared coauthors
- enrichment ror differs: 00js3aw79 vs 01ej9dk98

**Conflicting evidence:**
- Same venueId S4210210321

**Limitations / missing information:**
- A mention has no ORCID

<details><summary>Evidence references</summary>

- A `work` `er-evidence:a13f1a83ae0eb7d63c89e205ca9c28403c945f5c5b452d523a3bb8883f749186` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:270`
- A `enrichment` `er-evidence:fa1c79ef9f78d1349e85d69abbbeafb8f589233545857bf1aaf9d0de36eea9cc` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2926`
- B `enrichment` `er-evidence:673776b1a4a3e6d55fe3baf4c4237c88901b5ce1f102572a71d119b4f813f218` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:913`
- B `work` `er-evidence:b1e8e5e4578976c370a5d08b1bbb20e5dd2e04ab53b68dd1fd4a297a096fbd0b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:82`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 191 — Work

- **pairId:** `resolution-pair:955fcb0695c13fc573bdc70780d9dbfcd36d7cd918e5033d1e15d084b2ac877e`
- **evidenceHash:** `b77347deec73fcb8a7a9b8abb0933ee64bed982dd7edbcabff94ea3aafe0810f`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | CROSSREF 10.1145/3299887.3299895 (journal-article) | OPENALEX W2904420164 (article) |
| Title | Paris Koutris Speaks Out on a Theoretical Model for Query Processing | Paris Koutris Speaks Out on a Theoretical Model for Query Processing |
| Year | 2018 | 2018 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S47508943 |
| DOI | 10.1145/3299887.3299895 | 10.1145/3299887.3299895 |
| arXiv ID | — | — |
| Pages | 48-50 | 48-50 |
| Authors | (2) Marianne Winslett, Vanessa Braganholo | (2) Marianne Winslett, Vanessa Braganholo |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3299887.3299895, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3299887.3299895, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3299887.3299895'] B=['10.1145/3299887.3299895'] -> equal_

**AI-proposed label: `same`**

**Note:** Crossref and OpenAlex records share DOI 10.1145/3299887.3299895, the title "Paris Koutris Speaks Out on a Theoretical Model for Query Processing", year 2018, pages 48-50 and authors Marianne Winslett and Vanessa Braganholo.

**Supporting evidence:**
- Normalized DOI equal
- Identical title, year, pages and author list

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:c28efcdad4b3172e70b3cb562d8cfa56e1cf73065a400fdc86d5feacb85659ed` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:9`
- B `work` `er-evidence:8632243e84143c083b659b0829d1e1f1a938bb3cd844fde4f38727849317e92e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:369`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 192 — Work

- **pairId:** `resolution-pair:2229889f3141135a16bc500593d96649fd8c38bec24a755d4df971c145f1ba98`
- **evidenceHash:** `8e044fcadd4427ec2250d08182e177f8baaedad53a8f8a33593bc31ad3175fc6`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3174659798 (article) | OPENALEX W4389539730 (article) |
| Title | Rearchitecting Linux Storage Stack for µs Latency and High Throughput | Language Models Enable Simple Systems for Generating Structured Views of Heterogeneous Data Lakes |
| Year | 2021 | 2023 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210226185 |
| DOI | — | 10.14778/3626292.3626294 |
| arXiv ID | — | — |
| Pages | 113-128 | 92-105 |
| Authors | (4) Jaehyun Hwang, Midhul Vuppalapati, Simon Peter, Rachit Agarwal | (7) Simran Arora, Brandon Yang, Sabri Eyuboglu, Avanika Narayan, Andrew Hojel, Immanuel Trummer, Christopher Ré |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.14778/3626292.3626294, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3626292.3626294, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.14778/3626292.3626294'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Rearchitecting Linux Storage Stack for µs Latency and High Throughput" (no DOI, OSDI 2021) and B "Language Models Enable Simple Systems for Generating Structured Views…" (10.14778/3626292.3626294, 2023) have unrelated titles and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2021 vs 2023
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:18cd80b4a21c60deca8ffe5dcc8f34ca0ea968bdbe9ce4869391b7f37eae18a3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:205`
- B `work` `er-evidence:b52af49df5e710c14d8349165a45d91793cb3fceb4b5312cc67eb17813b99805` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:55`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 193 — Work

- **pairId:** `resolution-pair:24219eaa999577b911eeb97c5ef9b08ea772794fb6caf725eb0e83725fd82a40`
- **evidenceHash:** `85957346a8a601b13c483a1b48e102c65873b6f2fc8849ae8cff623bf696eb90`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3028864969 (conference-paper) | OPENALEX W3029532343 (conference-paper) |
| Title | SONG: Approximate Nearest Neighbor Search on GPU | LISA: A Learned Index Structure for Spatial Data |
| Year | 2020 | 2020 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4393915683 |
| DOI | 10.1109/icde48307.2020.00094 | 10.1145/3318464.3389703 |
| arXiv ID | — | — |
| Pages | 1033-1044 | 2119-2133 |
| Authors | (3) Weijie Zhao, Shulong Tan, Ping Li | (5) Pengfei Li, Hua Lu, Qian Zheng, Long Yang, Gang Pan |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde48307.2020.00094, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde48307.2020.00094, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3318464.3389703, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3318464.3389703, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1109/icde48307.2020.00094'] B=['10.1145/3318464.3389703'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "SONG: Approximate Nearest Neighbor Search on GPU" (10.1109/icde48307.2020.00094) and B "LISA: A Learned Index Structure for Spatial Data" (10.1145/3318464.3389703) are both 2020 but have distinct DOIs, different titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title different
- venueId S4210210321 vs S4393915683
- work.authors disjoint

**Conflicting evidence:**
- Same year 2020

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:1466a1d1d5a108ca8de5ef161f0c92fe4e99b13ee8c9d611b4737b1f7670793f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:286`
- B `work` `er-evidence:5845ecf81e1aea8cd6569dc65a437eb74a641a8427cf37d2eaefc0b5d147b6a1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:282`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 194 — Researcher

- **pairId:** `resolution-pair:7c632fef267416786e16b22842eba72642df5aa5c241c11d471f8977279bee22`
- **evidenceHash:** `a1f5a71243e28a502456f703cdaf9715ca58b294d1def5df79beac05ce40d5de`
- **Question:** do mention A `mention:openalex:W3096566397#2` and B `mention:openalex:W4385270681#5` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3096566397#2 | mention:openalex:W4385270681#5 |
| Name as written | Cheng Li | Chao Li |
| Author position | 2 of 5 | 5 of 6 |
| ORCID on mention | 0000-0003-3611-1055 (OpenAlex-supplied) | 0000-0002-6208-8269 (OpenAlex-supplied) |
| OpenAlex author ID | A5100354225 | A5100323216 |
| Affiliation | ROR 04c4dkn09 | ROR 00wk2mp56 |
| Work title | PaGraph | Self-supervised Trajectory Representation Learning with Temporal Regularities and Travel Semantics |
| Year | 2020 | 2023 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4210210321 |
| DOI | 10.1145/3419111.3421281 | 10.1109/icde55515.2023.00070 |
| Coauthors | Zhiqi Lin, Youshan Miao, Yunxin Liu, Yinlong Xu | Jiawei Jiang, Dayan Pan, Houxing Ren, Xiaohan Jiang, Jingyuan Wang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['04c4dkn09'] B=['00wk2mp56'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#2 "Cheng Li" and B author#5 "Chao Li" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Cheng" vs "Chao"
- No shared coauthors
- enrichment ror differs: 04c4dkn09 vs 00wk2mp56
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:6a35eb036f260be557a5efb3f5de428ef7279fffabf3c4e72dc319bb6cd0030f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:242`
- A `enrichment` `er-evidence:a248cb674c1876bab6f456986c97b65374d6abd95eeb859ba6002755d1d5a71f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2630`
- B `work` `er-evidence:05392bfc3e248b7c54c794c7f6efd90c9f6e1b081dc74f4f6542f4fdeb41f6c3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:89`
- B `enrichment` `er-evidence:2796a4154d2e93524e7877435fec008c712b2f73c83e7481b96e3d53f9d6eed1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:979`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 195 — Work

- **pairId:** `resolution-pair:f4ad1bc9d088117deea34985b42fdf13a39e090466d8cb5147f6689afd80cdec`
- **evidenceHash:** `3fe5aa88d6be6041486680017e4255d7dc68e3fb50ec61792fd226114ca07e90`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0002-0425-2462/work/79597276 | ORCID activity 0000-0002-0425-2462/work/79597278 |
| Title | XML materialized views in P2P networks | XML materialized views in P2P networks |
| Year | publicationYear=2009 | publicationYear=2009 |
| Venue ID | — | — |
| DOI | — | — |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0002-0425-2462 (author list not supplied) | ORCID record owner 0000-0002-0425-2462 (author list not supplied) |
| Observed identifiers | uri=https://hal.inria.fr/inria-00431668 (self) | uri=https://hal.inria.fr/inria-00425627 (self) |

_helper: normalized DOI A=- B=- -> not comparable_

**AI-proposed label: `uncertain`** — flags: `VERSION_RELATIONSHIP`

**Note:** Two activities on ORCID record 0000-0002-0425-2462 share the title "XML materialized views in P2P networks" and year 2009 but point to two different HAL deposits (inria-00431668 vs inria-00425627) with no DOI. They may be duplicate deposits or different versions (e.g. report vs paper); the evidence cannot tell.

**Supporting evidence:**
- orcid-activity.title identical
- publicationYear 2009 on both
- Same ORCID record owner

**Conflicting evidence:**
- Distinct self identifiers: uri=https://hal.inria.fr/inria-00431668 vs uri=https://hal.inria.fr/inria-00425627 (not DOIs)

**Limitations / missing information:**
- No DOI, author list, venue or pages supplied

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:c2f4b69d886f7a2017c4c8579de94df6c4678466528c0ccffdd5f5abc57762c7` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:75`
- B `orcid-activity` `er-evidence:33607a8288156e26cfa412e71fe9f8cb339168e549a433f2fbfd034bc5842d65` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:73`

</details>

**Danny's decision:** ☐ same ☐ different ☑ uncertain

**Comments:**

> 

---

## Task 196 — Work

- **pairId:** `resolution-pair:724fa484ec4547b110589322aeb86199b71662cd0c021ff126d0bf44b9d8e717`
- **evidenceHash:** `25293aa96aa2b40b323bcf64acd3a28c5ddd28330b36df1daa01176930a52b94`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2659288104 (conference-paper) | OPENALEX W2904324473 (article) |
| Title | When Can We Answer Queries Using Result-Bounded Data Interfaces? | Logic-based Perspectives on Query Reformulationover Restricted Interfaces |
| Year | 2018 | 2018 |
| Venue ID | venue:openalex:S7407087293 | venue:openalex:S47508943 |
| DOI | 10.1145/3196959.3196965 | 10.1145/3299887.3299889 |
| arXiv ID | — | — |
| Pages | 281-293 | 5-16 |
| Authors | (2) Antoine Amarilli, Michael Benedikt | (1) Michael Benedikt |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3196959.3196965, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3196959.3196965, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3299887.3299889, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3299887.3299889, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3196959.3196965'] B=['10.1145/3299887.3299889'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "When Can We Answer Queries Using Result-Bounded Data Interfaces?" (10.1145/3196959.3196965, Amarilli & Benedikt) and B "Logic-based Perspectives on Query Reformulation over Restricted Interfaces" (OpenAlex, 10.1145/3299887.3299889, Benedikt alone) have distinct DOIs and different titles.

**Supporting evidence:**
- work.doi distinct
- work.title different
- Author lists differ (2 vs 1)
- venueId S7407087293 vs S47508943; pages 281-293 vs 5-16

**Conflicting evidence:**
- Same year 2018; shared author Michael Benedikt; related topic

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:46da9c0da019a9220596b8fc699e9c2e066bc33eabde9ba9561b57a9d0bb0bf0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:445`
- B `work` `er-evidence:0ef77317d84c100171fe86ce78fa7976f99ec20778a7f3a6a1fcba9f488110ab` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:370`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 197 — Work

- **pairId:** `resolution-pair:0bc83ff4908cdd461141752e4b6e897fb6120e6bdd9b6f30cfdf1e4c16ee8b28`
- **evidenceHash:** `f2f055e781462fe2fe9dd9b308175483420a03667e1e3018e69cff5dbe9ff388`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W4321448364 (article) | OPENALEX W4400909749 (conference-paper) |
| Title | Can Foundation Models Wrangle Your Data? | CAGRA: Highly Parallel Graph Construction and Approximate Nearest Neighbor Search for GPUs |
| Year | 2022 | 2024 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210210321 |
| DOI | 10.14778/3574245.3574258 | 10.1109/icde60146.2024.00323 |
| arXiv ID | — | — |
| Pages | 738-746 | 4236-4247 |
| Authors | (4) Avanika Narayan, Ines Chami, Laurel Orr, Christopher Ré | (6) Hiroyuki Ootomo, Akira Naruse, Corey Nolet, Ray Wang, Tamas Feher, Yong Wang |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3574245.3574258, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3574245.3574258, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1109/icde60146.2024.00323, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde60146.2024.00323, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.14778/3574245.3574258'] B=['10.1109/icde60146.2024.00323'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Can Foundation Models Wrangle Your Data?" (10.14778/3574245.3574258, 2022) and B "CAGRA: Highly Parallel Graph Construction…" (10.1109/icde60146.2024.00323, 2024) have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2022 vs 2024
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:5b00867f970a5bca6056c318e8e5eaf60e59901419bcf201a8af72e9e1c80b4e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:119`
- B `work` `er-evidence:1bf5bf18fdd700f45ad7266e084cc85448ca79dc7a483fdc361cb436d6c35685` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:29`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 198 — Researcher

- **pairId:** `resolution-pair:61e01f2d63992d8d47dfc6f9d4aeb895aca0d1a7d9d3b39f34554688efbab101`
- **evidenceHash:** `22b5645da9b08cf22e8ad620fe3e6255ad49543a0fee5379276bfb4cbef76474`
- **Question:** do mention A `mention:openalex:W2948742909#3` and B `mention:openalex:W4385270120#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2948742909#3 | mention:openalex:W4385270120#2 |
| Name as written | H. Howie Huang | Han Huang |
| Author position | 3 of 3 | 2 of 6 |
| ORCID on mention | 0000-0001-8588-7680 (OpenAlex-supplied) | — |
| OpenAlex author ID | A5002254350 | — |
| Affiliation | ROR 00y4zzh67 | ROR 00wk2mp56; ROR 017r4dj03 |
| Work title | CECI | PriSTI: A Conditional Diffusion Framework for Spatiotemporal Imputation |
| Year | 2019 | 2023 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210210321 |
| DOI | 10.1145/3299869.3300086 | 10.1109/icde55515.2023.00150 |
| Coauthors | Bibek Bhattarai, Hang Liu | Mingzhe Liu, Hao Feng, Leilei Sun, Bowen Du, Yanjie Fu |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00y4zzh67'] B=['00wk2mp56', '017r4dj03'] shared=none_

**AI-proposed label: `uncertain`**

**Note:** A "H. Howie Huang" and B "Han Huang" are not clearly incompatible (initial H. could stand for Han), but nothing corroborates a match: no shared coauthors, disjoint RORs (00y4zzh67 vs 00wk2mp56/017r4dj03) and different topics (subgraph matching "CECI" 2019; spatiotemporal imputation 2023).

**Supporting evidence:**
- Surname match; initial H. compatible with given name Han

**Conflicting evidence:**
- No shared coauthors
- enrichment ror sets disjoint
- A uses the distinct form 'Howie' as a middle/preferred name

**Limitations / missing information:**
- B mention has no ORCID; A observedOrcid is OpenAlex-supplied only
- Neither identity nor difference is established

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:2c84d1cc0603594a5141fb2dd04f6580352f6b4050d4454ea913128456bfc6a3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3606`
- A `work` `er-evidence:c7700418e0e4bbefbb270ab774e4739b0c8877c2f95ba4d11f3810ba35dc2c6f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:345`
- B `work` `er-evidence:7a65b97839d5f62c7d6d1d5a09b2bcc1d929bf2f97a147db9b61e7d4ae171cd8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:94`
- B `enrichment` `er-evidence:ae7b05caa3e15a7b3cf4bb9639d19d77657dc4fa3b96a1955bfe2d98f22e25ed` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1029`
- B `enrichment` `er-evidence:dff1547c2775ba7f487ad179e48f9cbf80fbdaaab8679b3bb542a55ae26ca395` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1028`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Semantic Scholar assigns different author IDs; ORCID 0000-0001-8588-7680 (H Howie Huang, 251 works) lists CECI but not PriSTI.

---

## Task 199 — Work

- **pairId:** `resolution-pair:1232fa4eab3beed470bbca63b9a50c1ca83df2a6347797b8c6e7f0bda6679abd`
- **evidenceHash:** `98e0ca9940a4f45e82736ec167751c1dd36cc400df5f555298749070a8e3e843`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | CROSSREF 10.1145/3299887.3299889 (journal-article) | OPENALEX W4311994618 (article) |
| Title | Logic-based Perspectives on Query Reformulationover Restricted Interfaces | Rewriting the infinite chase |
| Year | 2018 | 2022 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S4210226185 |
| DOI | 10.1145/3299887.3299889 | 10.14778/3551793.3551851 |
| arXiv ID | — | — |
| Pages | 5-16 | 3045-3057 |
| Authors | (1) Michael Benedikt | (5) Michael Benedikt, Maxime Buron, Stefano Germano, Kevin Kappelmann, Boris Motik |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.14778/3551793.3551851, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3551793.3551851, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3299887.3299889'] B=['10.14778/3551793.3551851'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Logic-based Perspectives on Query Reformulation over Restricted Interfaces" (10.1145/3299887.3299889, 2018) and B "Rewriting the infinite chase" (10.14778/3551793.3551851, 2022) have distinct DOIs and different titles; only Michael Benedikt is shared.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2018 vs 2022
- Author lists differ (1 vs 5)

**Conflicting evidence:**
- Shared author Michael Benedikt

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:9a525f2d788aa1d202be967926aee60c9e9c0ed6c1feb44d1825541a4606fd27` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:7`
- B `work` `er-evidence:d5e2eaaadb905d03baa7c676f0ae505d544cb44b645f4f0ba7af46badd1985df` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:126`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 200 — Work

- **pairId:** `resolution-pair:5f1a1bf18692d61569d1930fd88a85d3fa805a479e1994bfc96e4499164ff42a`
- **evidenceHash:** `f9ae225b4b7c7b8a2a940bbc48620ef293f0f9101e3a77751b6b21a1608597dc`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | CROSSREF 10.1145/3277006.3277014 (journal-article) | OPENALEX W2890351236 (article) |
| Title | Technical Perspective: | Technical Perspective: |
| Year | 2018 | 2018 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S47508943 |
| DOI | 10.1145/3277006.3277014 | 10.1145/3277006.3277014 |
| arXiv ID | — | — |
| Pages | 32-32 | 32-32 |
| Authors | (1) Wang-Chiew Tan | (1) Wang-Chiew Tan |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3277006.3277014, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3277006.3277014, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3277006.3277014'] B=['10.1145/3277006.3277014'] -> equal_

**AI-proposed label: `same`**

**Note:** Crossref and OpenAlex records share DOI 10.1145/3277006.3277014, title "Technical Perspective:", year 2018, page 32-32 and sole author Wang-Chiew Tan.

**Supporting evidence:**
- Normalized DOI equal
- Identical (truncated) title, year, pages and author

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- Title is truncated in both sources

<details><summary>Evidence references</summary>

- A `work` `er-evidence:b2cd33fb5ab4fa0f2cd7966e6a6293640ee881fdfde870a4d157ccc0f66553b9` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:5`
- B `work` `er-evidence:de4e20c1ee188085a54aefc8635f24910c74be6f6a6ce93bb60439ba2050f9c7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:398`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

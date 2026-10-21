# ScholarChain AI review drafts — batch 11 (tasks 201–220)

> **Status: AI_SUGGESTIONS_PENDING_HUMAN_REVIEW.** These are AI-generated suggestions from a session-reported `claude-opus-5-5` model (not independently verified). They are not human reviews or gold labels. Record your own decision in each task's decision box; an empty box means not reviewed.

Queue: `review-queue:05c5817f62a70d378829be361b9c9169fc9af18448f7c83c245f1d65bbca6175`  
Work tasks: 13 · Researcher tasks: 7

Rows marked `>> … <<` in the raw data and the 'Name as written' row identify the mention being compared. OpenAlex author IDs and OpenAlex-supplied ORCIDs are provider hypotheses. Lines in _italics_ starting with 'helper:' are exact-string comparisons computed by a script to help reading; they are not judgments.

---
## Task 201 — Researcher

- **pairId:** `resolution-pair:4bc44414385a79dd1c30ffe1901f44fd06b07914451c87895921c0395d842c3e`
- **evidenceHash:** `2c67ec710b737b0819f1d789d6fcadbd8bab53d669e465d9f22d6d36267f9c99`
- **Question:** do mention A `mention:openalex:W2659288104#2` and B `mention:openalex:W2904324473#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2659288104#2 | mention:openalex:W2904324473#1 |
| Name as written | Michael Benedikt | Michael Benedikt |
| Author position | 2 of 2 | 1 of 1 |
| ORCID on mention | 0000-0003-2964-0880 (OpenAlex-supplied) | 0000-0003-2964-0880 (OpenAlex-supplied) |
| OpenAlex author ID | A5037774973 | A5037774973 |
| Affiliation | ROR 052gg0110 | ROR 052gg0110 |
| Work title | When Can We Answer Queries Using Result-Bounded Data Interfaces? | Logic-based Perspectives on Query Reformulationover Restricted Interfaces |
| Year | 2018 | 2018 |
| Venue ID | venue:openalex:S7407087293 | venue:openalex:S47508943 |
| DOI | 10.1145/3196959.3196965 | 10.1145/3299887.3299889 |
| Coauthors | Antoine Amarilli | — |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['052gg0110'] B=['052gg0110'] shared=['052gg0110']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Michael Benedikt" with ROR 052gg0110 in 2018 on closely related topics: "When Can We Answer Queries Using Result-Bounded Data Interfaces?" and "Logic-based Perspectives on Query Reformulation over Restricted Interfaces".

**Supporting evidence:**
- Name exact match: A author#2, B author#1 (sole author)
- enrichment ror=052gg0110 on both target mentions
- Specific topic continuity: query answering over restricted/result-bounded interfaces
- Same year 2018
- Same OpenAlex-supplied observedOrcid 0000-0003-2964-0880 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors (B is single-authored)

**Limitations / missing information:**
- Relies on name, affiliation and topic

<details><summary>Evidence references</summary>

- A `work` `er-evidence:46da9c0da019a9220596b8fc699e9c2e066bc33eabde9ba9561b57a9d0bb0bf0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:445`
- A `enrichment` `er-evidence:a6e9da00e5dd2d1bff1c6ca49c3d91c635b528f8b1e1c327f8fb232e03f5376e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4509`
- B `work` `er-evidence:0ef77317d84c100171fe86ce78fa7976f99ec20778a7f3a6a1fcba9f488110ab` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:370`
- B `enrichment` `er-evidence:8b39532294c98ed2f7dc215f83ada1247b78556efd92331c044db0cbed8a1dae` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3845`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 202 — Work

- **pairId:** `resolution-pair:3843e9f5c0b11b4b8e6aa2c2bd6f0715d0815bcc466beac12e3cd8c716197df2`
- **evidenceHash:** `543e72f2382656bcf20702f6bac23d3543424c99f6e9db1a5dff56e71eef79f3`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0002-6698-2735/work/132962095 | ORCID activity 0000-0002-6698-2735/work/60530746 |
| Title | Order-Invariant Types and Their Applications | Order-Invariant Types and their Applications |
| Year | publicationYear=2016 | publicationYear=2016 |
| Venue ID | — | — |
| DOI | 10.2168/lmcs-12(1:9)2016 | 10.2168/lmcs-12(1:9)2016 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0002-6698-2735 (author list not supplied) | ORCID record owner 0000-0002-6698-2735 (author list not supplied) |
| Observed identifiers | doi=10.2168/LMCS-12(1:9)2016 (self) | source-work-id=09841ccf-0a2c-4266-9010-bb4ec6fd5225 (self); eid=2-s2.0-84962423399 (self); doi=10.2168/LMCS-12(1:9)2016 (self) |

_helper: normalized DOI A=['10.2168/lmcs-12(1:9)2016'] B=['10.2168/lmcs-12(1:9)2016'] -> equal_

**AI-proposed label: `same`**

**Note:** Two activities on ORCID record 0000-0002-6698-2735 carry the same DOI 10.2168/lmcs-12(1:9)2016, the title "Order-Invariant Types and Their/their Applications" and publicationYear 2016.

**Supporting evidence:**
- Normalized observedDoi equal: 10.2168/lmcs-12(1:9)2016
- Title identical apart from capitalization
- Same year and ORCID record owner

**Conflicting evidence:**
- Distinct activity ids; B additionally lists eid=2-s2.0-84962423399 and a source-work-id (duplicate entries from different sources)

**Limitations / missing information:**
- No author list, venue or pages in ORCID activities

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:a9b57edf00f6a5d0ce9d3aab26da8c2212e8201f869818bd9ae459382e766c23` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:465`
- B `orcid-activity` `er-evidence:af74a7cd89e0176104681683e39b1f70230befe23ce818bed7b72cc8f4d0935a` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:336`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 203 — Work

- **pairId:** `resolution-pair:500618a58fd719447bebf86b92aa44e57c44072b455b7c104eefeb52a75f6537`
- **evidenceHash:** `34b6dd4daf9e08ee6f28250af78b99ac8f13ac2536e8d7d97e28bb49b0d29197`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W4387321503 (conference-paper) | OPENALEX W4387321622 (conference-paper) |
| Title | Paella: Low-latency Model Serving with Software-defined GPU Scheduling | Private Web Search with Tiptoe |
| Year | 2023 | 2023 |
| Venue ID | venue:openalex:S4306420989 | venue:openalex:S4306420989 |
| DOI | 10.1145/3600006.3613163 | 10.1145/3600006.3613134 |
| arXiv ID | — | — |
| Pages | 595-610 | 396-416 |
| Authors | (3) Kelvin K. W. Ng, Henri Maxime Demoulin, Vincent Liu | (4) Alexandra Henzinger, Emma Dauterman, Henry Corrigan-Gibbs, Nickolai Zeldovich |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3600006.3613163, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3600006.3613163, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3600006.3613134, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3600006.3613134, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3600006.3613163'] B=['10.1145/3600006.3613134'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Paella: Low-latency Model Serving with Software-defined GPU Scheduling" (10.1145/3600006.3613163) and B "Private Web Search with Tiptoe" (10.1145/3600006.3613134) are both 2023 in venue S4306420989 but have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- pages 595-610 vs 396-416
- work.authors disjoint

**Conflicting evidence:**
- Same year 2023 and venueId

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:6f072eed471b3ff7ec86adfb260e85d88fb7b0991218f1807f8617df9d00ba94` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:71`
- B `work` `er-evidence:706d724744665631c550f8bc3a3f9ecd4a4a862ac85ad3584f821c17d72203f1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:69`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 204 — Work

- **pairId:** `resolution-pair:e208891312e08d257fb654de9466e73d489e2ff5f100d6281c6e01d472c0baac`
- **evidenceHash:** `bfa2bc7b27d75d0f9e984a84ec6f49777daddf5ff0f97ec0f666a55c407e230d`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2659288104 (conference-paper) | OPENALEX W3093150360 (conference-paper) |
| Title | When Can We Answer Queries Using Result-Bounded Data Interfaces? | Wukong |
| Year | 2018 | 2020 |
| Venue ID | venue:openalex:S7407087293 | venue:openalex:S7407088165 |
| DOI | 10.1145/3196959.3196965 | 10.1145/3419111.3421286 |
| arXiv ID | — | — |
| Pages | 281-293 | 1-15 |
| Authors | (2) Antoine Amarilli, Michael Benedikt | (6) Benjamin Carver, Jingyuan Zhang, Ao Wang, Ali Anwar, Panruo Wu, Yue Cheng |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3196959.3196965, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3196959.3196965, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3419111.3421286, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3419111.3421286, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3196959.3196965'] B=['10.1145/3419111.3421286'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "When Can We Answer Queries Using Result-Bounded Data Interfaces?" (10.1145/3196959.3196965, 2018) and B "Wukong" (10.1145/3419111.3421286, 2020) have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2018 vs 2020
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:46da9c0da019a9220596b8fc699e9c2e066bc33eabde9ba9561b57a9d0bb0bf0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:445`
- B `work` `er-evidence:6c77b692abc917bba0450a486a0c8f4c190577093c28451fbc94494874b6b18a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:253`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 205 — Work

- **pairId:** `resolution-pair:6940fb1a63cf297b0c56dd07689b5bacaefe4c59991494b285f8415afe484e64`
- **evidenceHash:** `749fe1675513a008d24ba05f4b3260357f6bcfd3e80d45cc1e9980cb9f17025e`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3103950664 (article) | OPENALEX W4389539730 (article) |
| Title | Fault-tolerant and transactional stateful serverless workflows | Language Models Enable Simple Systems for Generating Structured Views of Heterogeneous Data Lakes |
| Year | 2020 | 2023 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210226185 |
| DOI | — | 10.14778/3626292.3626294 |
| arXiv ID | — | — |
| Pages | 1187-1204 | 92-105 |
| Authors | (5) Haoran Zhang, Adney Cardoza, Peter Baile Chen, Sebastian Angel, Vincent Liu | (7) Simran Arora, Brandon Yang, Sabri Eyuboglu, Avanika Narayan, Andrew Hojel, Immanuel Trummer, Christopher Ré |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.14778/3626292.3626294, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3626292.3626294, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.14778/3626292.3626294'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Fault-tolerant and transactional stateful serverless workflows" (no DOI, OSDI 2020) and B "Language Models Enable Simple Systems for Generating Structured Views…" (10.14778/3626292.3626294, 2023) have unrelated titles and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2020 vs 2023
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:a51a7d1dccfd085f01289aa5f94d4fdc5b557daecfd203f58d72be58d59749ae` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:229`
- B `work` `er-evidence:b52af49df5e710c14d8349165a45d91793cb3fceb4b5312cc67eb17813b99805` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:55`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 206 — Work

- **pairId:** `resolution-pair:6b0cf564763d224df095dcfa4fc485703ea2a80f7267e060ac86baf7f04aea52`
- **evidenceHash:** `ea9902832be6d513bad1d286865a62379db819781bb6774863567add01d97392`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2948742909 (conference-paper) | OPENALEX W3029532343 (conference-paper) |
| Title | CECI | LISA: A Learned Index Structure for Spatial Data |
| Year | 2019 | 2020 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4393915683 |
| DOI | 10.1145/3299869.3300086 | 10.1145/3318464.3389703 |
| arXiv ID | — | — |
| Pages | 1447-1462 | 2119-2133 |
| Authors | (3) Bibek Bhattarai, Hang Liu, H. Howie Huang | (5) Pengfei Li, Hua Lu, Qian Zheng, Long Yang, Gang Pan |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3299869.3300086, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3299869.3300086, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3318464.3389703, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3318464.3389703, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3299869.3300086'] B=['10.1145/3318464.3389703'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "CECI" (10.1145/3299869.3300086, 2019) and B "LISA: A Learned Index Structure for Spatial Data" (10.1145/3318464.3389703, 2020) have distinct DOIs, different titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2019 vs 2020
- work.authors disjoint

**Conflicting evidence:**
- Same venueId S4393915683

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:c7700418e0e4bbefbb270ab774e4739b0c8877c2f95ba4d11f3810ba35dc2c6f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:345`
- B `work` `er-evidence:5845ecf81e1aea8cd6569dc65a437eb74a641a8427cf37d2eaefc0b5d147b6a1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:282`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 207 — Researcher

- **pairId:** `resolution-pair:bd1f4a3e685c0c971fa58b10b490ec6d2af280a07bbec23291d1808147185dc2`
- **evidenceHash:** `c8f452136c3056f25b66ba26f3509e8609bbd6f665ece389fa86160dc7bfcb03`
- **Question:** do mention A `mention:openalex:W2897044322#6` and B `mention:openalex:W4400909749#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2897044322#6 | mention:openalex:W4400909749#4 |
| Name as written | Ruoyu Wang | Ray Wang |
| Author position | 6 of 7 | 4 of 6 |
| ORCID on mention | 0009-0000-6617-0369 (OpenAlex-supplied) | 0000-0001-8982-0571 (OpenAlex-supplied) |
| OpenAlex author ID | A5100653715 | A5100340000 |
| Affiliation | ROR 03efmqc40 | — |
| Work title | REPT: reverse debugging of failures in deployed software | CAGRA: Highly Parallel Graph Construction and Approximate Nearest Neighbor Search for GPUs |
| Year | 2018 | 2024 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210210321 |
| DOI | 10.5555/3291168.3291171 | 10.1109/icde60146.2024.00323 |
| Coauthors | Weidong Cui, Xinyang Ge, Baris Kasikci, Ben Niu, Upamanyu Sharma, Insu Yun | Hiroyuki Ootomo, Akira Naruse, Corey Nolet, Tamas Feher, Yong Wang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['03efmqc40'] B=- shared=none_

**AI-proposed label: `different`**

**Note:** A author#6 "Ruoyu Wang" and B author#4 "Ray Wang" have different given names as written, no shared coauthors, unrelated topics (reverse debugging 2018; GPU nearest-neighbor search 2024) and different OpenAlex-supplied ORCIDs.

**Supporting evidence:**
- nameText given names differ: "Ruoyu" vs "Ray"
- No shared coauthors
- Different OpenAlex-supplied ORCIDs 0009-0000-6617-0369 vs 0000-0001-8982-0571 (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- "Ray" could be an adopted English name; if so the name difference would be weaker
- B has no affiliation evidence

<details><summary>Evidence references</summary>

- A `work` `er-evidence:85ad07193da71efc6d54a839e20e910917fe1c9a5ee24544bc6ab534dd607e1c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:386`
- A `enrichment` `er-evidence:9ce7095514d32798362abc97be94a3d49fde1aaca2b77254776d0089a5a4e9d1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3977`
- B `work` `er-evidence:1bf5bf18fdd700f45ad7266e084cc85448ca79dc7a483fdc361cb436d6c35685` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:29`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 208 — Researcher

- **pairId:** `resolution-pair:60830b465e5e37150080b8ed5856a41d515709ed355073a2cc4e65505fe50aa2`
- **evidenceHash:** `f848a4a306763b3cda57b6d29869aa279e2c39659e81b8b2887c84e9d64a1e19`
- **Question:** do mention A `mention:openalex:W2659288104#2` and B `mention:openalex:W4311994618#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2659288104#2 | mention:openalex:W4311994618#1 |
| Name as written | Michael Benedikt | Michael Benedikt |
| Author position | 2 of 2 | 1 of 5 |
| ORCID on mention | 0000-0003-2964-0880 (OpenAlex-supplied) | 0000-0003-2964-0880 (OpenAlex-supplied) |
| OpenAlex author ID | A5037774973 | A5037774973 |
| Affiliation | ROR 052gg0110 | ROR 052gg0110 |
| Work title | When Can We Answer Queries Using Result-Bounded Data Interfaces? | Rewriting the infinite chase |
| Year | 2018 | 2022 |
| Venue ID | venue:openalex:S7407087293 | venue:openalex:S4210226185 |
| DOI | 10.1145/3196959.3196965 | 10.14778/3551793.3551851 |
| Coauthors | Antoine Amarilli | Maxime Buron, Stefano Germano, Kevin Kappelmann, Boris Motik |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['052gg0110'] B=['052gg0110'] shared=['052gg0110']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Michael Benedikt" with ROR 052gg0110 on logic-based query-answering papers ("When Can We Answer Queries Using Result-Bounded Data Interfaces?" 2018; "Rewriting the infinite chase" 2022).

**Supporting evidence:**
- Name exact match: A author#2, B author#1
- enrichment ror=052gg0110 on both target mentions
- Topic continuity: query answering/rewriting under constraints
- Same OpenAlex-supplied observedOrcid 0000-0003-2964-0880 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- Relies on name, affiliation and topic; a reviewer may prefer uncertain

<details><summary>Evidence references</summary>

- A `work` `er-evidence:46da9c0da019a9220596b8fc699e9c2e066bc33eabde9ba9561b57a9d0bb0bf0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:445`
- A `enrichment` `er-evidence:a6e9da00e5dd2d1bff1c6ca49c3d91c635b528f8b1e1c327f8fb232e03f5376e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4509`
- B `enrichment` `er-evidence:680578fdfa824647cb23600d4fbb8e2e26e679e6bc29906a8c018be7305e8fce` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1362`
- B `work` `er-evidence:d5e2eaaadb905d03baa7c676f0ae505d544cb44b645f4f0ba7af46badd1985df` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:126`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 209 — Work

- **pairId:** `resolution-pair:747b1d71047a6b27f83e5834f7d974002d606a67f4b761ad05b853c0c1a94f28`
- **evidenceHash:** `a1d6e6e86b04b8f5d0119f99d076d622a82806b0e2a8f80c7b6477f8db378f2a`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-0832-116X/work/151681305 | OPENALEX W3013397275 (article) |
| Title | Efficient Enumeration Algorithms for Regular Document Spanners | Efficient Enumeration Algorithms for Regular Document Spanners |
| Year | publicationYear=2020 | 2020 |
| Venue ID | — | venue:openalex:S90119964 |
| DOI | 10.1145/3351451 | 10.1145/3351451 |
| arXiv ID | — | — |
| Pages | — | 1-42 |
| Authors | ORCID record owner 0000-0003-0832-116X (author list not supplied) | (5) Fernando Florenzano, Cristian Riveros, Martín Ugarte, Stijn Vansummeren, Domagoj Vrgoč |
| Observed identifiers | doi=10.1145/3351451 (self); wosuid=WOS:000583687500004 (self) | namespace=openalex.doi, value=https://doi.org/10.1145/3351451, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3351451, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3351451'] B=['10.1145/3351451'] -> equal_

**AI-proposed label: `same`**

**Note:** ORCID activity 0000-0003-0832-116X/work/151681305 has observedDoi 10.1145/3351451 and title "Efficient Enumeration Algorithms for Regular Document Spanners" (2020), matching the OpenAlex work with the same DOI, title and year.

**Supporting evidence:**
- Normalized DOI equal: 10.1145/3351451
- Title identical
- Year 2020 on both

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- ORCID activity has no author list for comparison

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:e1e771a4867b20b27088de258f27a5a4a9a29a8e91daa32c26ca817d40fd171c` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:304`
- B `work` `er-evidence:0366818a398a6d1fc64f8ff2c5aee380c8acfae08e505908074bed20befb5593` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:292`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 210 — Work

- **pairId:** `resolution-pair:d79ca59866f9ae7d8e6fcf9b41ac935201cef034980b33449cfec3b38b5c419d`
- **evidenceHash:** `f623e2a5f6ca8509ce17a05ed963b524edde1051ff4a0787553690cefb2ec693`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | CROSSREF 10.1145/3299887.3299889 (journal-article) | OPENALEX W2904324473 (article) |
| Title | Logic-based Perspectives on Query Reformulationover Restricted Interfaces | Logic-based Perspectives on Query Reformulationover Restricted Interfaces |
| Year | 2018 | 2018 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S47508943 |
| DOI | 10.1145/3299887.3299889 | 10.1145/3299887.3299889 |
| arXiv ID | — | — |
| Pages | 5-16 | 5-16 |
| Authors | (1) Michael Benedikt | (1) Michael Benedikt |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3299887.3299889, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3299887.3299889, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3299887.3299889'] B=['10.1145/3299887.3299889'] -> equal_

**AI-proposed label: `same`**

**Note:** Crossref and OpenAlex records share DOI 10.1145/3299887.3299889, the title "Logic-based Perspectives on Query Reformulation over Restricted Interfaces", year 2018, pages 5-16 and sole author Michael Benedikt.

**Supporting evidence:**
- Normalized DOI equal
- Identical title, year, pages and author

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:9a525f2d788aa1d202be967926aee60c9e9c0ed6c1feb44d1825541a4606fd27` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:7`
- B `work` `er-evidence:0ef77317d84c100171fe86ce78fa7976f99ec20778a7f3a6a1fcba9f488110ab` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:370`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 211 — Work

- **pairId:** `resolution-pair:9b2116a507f62e7bc4f77b23c7335eabf1c6ba5372888153ebe41bd4487310f6`
- **evidenceHash:** `b95578c3ba9e1bf2b4073632bc7ae33f73ef56824ec78a5af7d70b9cc398094f`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3043413334 (article) | OPENALEX W3174659798 (article) |
| Title | Analyzing and mitigating data stalls in DNN training | Rearchitecting Linux Storage Stack for µs Latency and High Throughput |
| Year | 2021 | 2021 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4306420647 |
| DOI | 10.14778/3446095.3446100 | — |
| arXiv ID | — | — |
| Pages | 771-784 | 113-128 |
| Authors | (4) Jayashree Mohan, Amar Phanishayee, Ashish Raniwala, Vijay Chidambaram | (4) Jaehyun Hwang, Midhul Vuppalapati, Simon Peter, Rachit Agarwal |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3446095.3446100, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3446095.3446100, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.14778/3446095.3446100'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Analyzing and mitigating data stalls in DNN training" (DOI 10.14778/3446095.3446100) and B "Rearchitecting Linux Storage Stack for µs Latency and High Throughput" (no DOI) share only the year 2021; titles, venues and authors differ.

**Supporting evidence:**
- work.title different
- venueId S4210226185 vs S4306420647
- work.authors disjoint

**Conflicting evidence:**
- Same year 2021

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:77b036bbd65889087be36687fc27df3b9c8f6d2a0000dd28f9ac08b86a2ca35d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:263`
- B `work` `er-evidence:18cd80b4a21c60deca8ffe5dcc8f34ca0ea968bdbe9ce4869391b7f37eae18a3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:205`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 212 — Researcher

- **pairId:** `resolution-pair:f509a2001edc6f1b00b2eb4369c8820c6e250403b0842283cf34a80b343d1205`
- **evidenceHash:** `385db062b8faf9048bbe08c8a65386833d1a3acf1f4697357162492f395c2aff`
- **Question:** do mention A `mention:openalex:W4321448364#4` and B `mention:openalex:W4389539730#7` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4321448364#4 | mention:openalex:W4389539730#7 |
| Name as written | Christopher Ré | Christopher Ré |
| Author position | 4 of 4 | 7 of 7 |
| ORCID on mention | 0000-0002-4109-0108 (OpenAlex-supplied) | 0000-0002-4109-0108 (OpenAlex-supplied) |
| OpenAlex author ID | A5103852640 | A5103852640 |
| Affiliation | ROR 00f54p054 | ROR 00f54p054 |
| Work title | Can Foundation Models Wrangle Your Data? | Language Models Enable Simple Systems for Generating Structured Views of Heterogeneous Data Lakes |
| Year | 2022 | 2023 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210226185 |
| DOI | 10.14778/3574245.3574258 | 10.14778/3626292.3626294 |
| Coauthors | Avanika Narayan, Ines Chami, Laurel Orr | Simran Arora, Brandon Yang, Sabri Eyuboglu, Avanika Narayan, Andrew Hojel, Immanuel Trummer |

_helper: shared coauthor normalizedNames = ['avanika narayan']_
_helper: target-mention ROR A=['00f54p054'] B=['00f54p054'] shared=['00f54p054']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Christopher Ré" with shared coauthor Avanika Narayan, the same ROR 00f54p054, and foundation-models-for-data topics ("Can Foundation Models Wrangle Your Data?" 2022; "Language Models Enable Simple Systems…Data Lakes" 2023).

**Supporting evidence:**
- Name exact match: A author#4, B author#7
- Shared coauthor in payload: Avanika Narayan
- enrichment ror=00f54p054 on both target mentions
- Specific topic continuity
- Same OpenAlex-supplied observedOrcid 0000-0002-4109-0108 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- All hints OpenAlex-derived

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:3b4ab22f5742d8fc73b082399a36cbf059d6832a9bc0a963f2b72cf4022eac97` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1313`
- A `work` `er-evidence:5b00867f970a5bca6056c318e8e5eaf60e59901419bcf201a8af72e9e1c80b4e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:119`
- B `work` `er-evidence:b52af49df5e710c14d8349165a45d91793cb3fceb4b5312cc67eb17813b99805` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:55`
- B `enrichment` `er-evidence:fdddf3d8b61cf9924f12a70b799d8668cfebada7619682e44139d835ab3c9e94` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:616`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 213 — Work

- **pairId:** `resolution-pair:b15ebbbbd884fafa4fef211fa8a39814f523fd91885cab65fc28d091d0406c39`
- **evidenceHash:** `a18cfd0e3eb26ef0b77e34fe6982fe264dd41f274632315103bac9c7c944d1e7`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0002-6698-2735/work/132962092 | ORCID activity 0000-0002-6698-2735/work/60530693 |
| Title | First-Order and Temporal Logics for Nested Words | First-Order and Temporal Logics for Nested Words |
| Year | publicationYear=2008 | publicationYear=2008 |
| Venue ID | — | — |
| DOI | 10.2168/lmcs-4(4:11)2008 | 10.2168/lmcs-4(4:11)2008 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0002-6698-2735 (author list not supplied) | ORCID record owner 0000-0002-6698-2735 (author list not supplied) |
| Observed identifiers | doi=10.2168/LMCS-4(4:11)2008 (self) | source-work-id=699710f7-528d-4d7a-b8fb-7781a0aabb85 (self); eid=2-s2.0-77951117981 (self); doi=10.2168/LMCS-4(4:11)2008 (self) |

_helper: normalized DOI A=['10.2168/lmcs-4(4:11)2008'] B=['10.2168/lmcs-4(4:11)2008'] -> equal_

**AI-proposed label: `same`**

**Note:** Two activities on ORCID record 0000-0002-6698-2735 carry the same DOI 10.2168/lmcs-4(4:11)2008, the identical title "First-Order and Temporal Logics for Nested Words" and publicationYear 2008.

**Supporting evidence:**
- Normalized observedDoi equal
- Identical title
- Same year and ORCID record owner

**Conflicting evidence:**
- Distinct activity ids; B adds eid=2-s2.0-77951117981 and a source-work-id (duplicate entries from different sources)

**Limitations / missing information:**
- No author list, venue or pages

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:1ba820fbf27f95c7759412668597b5406a5b251887a099186c7a660e0aa0860e` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:2`
- B `orcid-activity` `er-evidence:a1832e00725daddf31749be7390e842d0e199b425646489976fdbc9f0a3e4d8b` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:389`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 214 — Work

- **pairId:** `resolution-pair:bbeada3880d047437365efbfb4670d0ab749183f51f0508a4fe49296755e9ce4`
- **evidenceHash:** `345fb9b7a69901f2fcc5769405d65f2df9960998526aa48e038f0f3039cc5079`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-1547-2847/work/112966395 | ORCID activity 0000-0003-1547-2847/work/113367189 |
| Title | Protecting Decision Boundary of Machine Learning Model With Differentially Private Perturbation | Protecting Decision Boundary of Machine Learning Model With Differentially Private Perturbation |
| Year | publicationYear=2022 | publicationYear=2022 |
| Venue ID | — | — |
| DOI | 10.1109/tdsc.2020.3043382 | 10.1109/tdsc.2020.3043382 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0003-1547-2847 (author list not supplied) | ORCID record owner 0000-0003-1547-2847 (author list not supplied) |
| Observed identifiers | doi=10.1109/TDSC.2020.3043382 (self) | doi=10.1109/tdsc.2020.3043382 (self); issn=1545-5971 (part-of); issn=1941-0018 (part-of); issn=2160-9209 (part-of) |

_helper: normalized DOI A=['10.1109/tdsc.2020.3043382'] B=['10.1109/tdsc.2020.3043382'] -> equal_

**AI-proposed label: `same`**

**Note:** Two activities on ORCID record 0000-0003-1547-2847 carry the same DOI 10.1109/tdsc.2020.3043382, the identical title "Protecting Decision Boundary of Machine Learning Model With Differentially Private Perturbation" and publicationYear 2022.

**Supporting evidence:**
- Normalized observedDoi equal
- Identical title
- Same year and ORCID record owner

**Conflicting evidence:**
- Distinct activity ids; B adds ISSN part-of references (duplicate entries)

**Limitations / missing information:**
- No author list or pages

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:0c7c4f128e0ed931c364db999529156253f7c1e78c4999bd582c9b0481d67e94` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:225`
- B `orcid-activity` `er-evidence:79740cb6f4d24164bfde376c9582faddf48d17e9f7b35e5f6539f16ee22174a8` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:235`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 215 — Researcher

- **pairId:** `resolution-pair:713a108e9341fa7dd2ad7c8062be4c5378bf5836fb4be40c153bc7a0bd12fb10`
- **evidenceHash:** `dafdced9a2a0591053af62b353d08762d80545cc445acf964a634307db6095b4`
- **Question:** do mention A `mention:openalex:W4387321084#4` and B `mention:openalex:W4400909749#6` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4387321084#4 | mention:openalex:W4400909749#6 |
| Name as written | Yang Wang | Yong Wang |
| Author position | 4 of 6 | 6 of 6 |
| ORCID on mention | 0000-0002-9721-4923 (OpenAlex-supplied) | 0009-0005-0906-8778 (OpenAlex-supplied) |
| OpenAlex author ID | A5100322850 | A5101762937 |
| Affiliation | ROR 00rs6vg23 | — |
| Work title | Understanding Silent Data Corruptions in a Large Production CPU Population | CAGRA: Highly Parallel Graph Construction and Approximate Nearest Neighbor Search for GPUs |
| Year | 2023 | 2024 |
| Venue ID | venue:openalex:S4306420989 | venue:openalex:S4210210321 |
| DOI | 10.1145/3600006.3613149 | 10.1109/icde60146.2024.00323 |
| Coauthors | Shaobu Wang, Guangyan Zhang, Junyu Wei, Jiesheng Wu, Qingchao Luo | Hiroyuki Ootomo, Akira Naruse, Corey Nolet, Ray Wang, Tamas Feher |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00rs6vg23'] B=- shared=none_

**AI-proposed label: `different`**

**Note:** A author#4 "Yang Wang" and B author#6 "Yong Wang" differ in given name (Yang vs Yong); no coauthor overlap.

**Supporting evidence:**
- nameText given names differ: "Yang" vs "Yong"
- No shared coauthors
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no affiliation evidence

<details><summary>Evidence references</summary>

- A `work` `er-evidence:329a9a8a733b5b219e36963afeea58dbd45476bf4c0d6292dfbcca66479c3447` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:75`
- A `enrichment` `er-evidence:68f0afe48d790c6ccc8c5eca35c48b57048523a2f185cde5ebd23185b40751a8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:826`
- B `work` `er-evidence:1bf5bf18fdd700f45ad7266e084cc85448ca79dc7a483fdc361cb436d6c35685` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:29`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 216 — Work

- **pairId:** `resolution-pair:a5dfcf229c1a8f63521d63a3b995a2e3596837a636e9407d211387fe561037fe`
- **evidenceHash:** `8852a91076aa956d0792ceb7b85ff7233f29e7e9533f0c88e2c7bb6dadd628ed`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0002-6698-2735/work/137256133 | OPENALEX W4381326861 (article) |
| Title | PG-Schema: Schemas for Property Graphs | PG-Schema: Schemas for Property Graphs |
| Year | publicationYear=2023 | 2023 |
| Venue ID | — | venue:openalex:S4387289859 |
| DOI | 10.1145/3589778 | 10.1145/3589778 |
| arXiv ID | — | — |
| Pages | — | 1-25 |
| Authors | ORCID record owner 0000-0002-6698-2735 (author list not supplied) | (21) Renzo Angles, Angela Bonifati, Stefania Dumbrava, George Fletcher, Alastair Green, Jan Hidders, Bei Li, Leonid Libkin, Victor Marsault, Wim Martens, Filip Murlak, Stefan Plantikow, Ognjen Savkovic, Michael Schmidt, Juan Sequeda … (+6 more) |
| Observed identifiers | doi=10.1145/3589778 (self) | namespace=openalex.doi, value=https://doi.org/10.1145/3589778, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3589778, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3589778'] B=['10.1145/3589778'] -> equal_

**AI-proposed label: `same`**

**Note:** ORCID activity 0000-0002-6698-2735/work/137256133 has observedDoi 10.1145/3589778 and title "PG-Schema: Schemas for Property Graphs" (2023), matching the OpenAlex work with the same DOI, title and year.

**Supporting evidence:**
- Normalized DOI equal: 10.1145/3589778
- Title identical
- Year 2023 on both

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- ORCID activity has no author list

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:d58a4df311cdde81deb45ec7924556a1812c6baa5601f9a2e88f1ddc9be0c091` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:461`
- B `work` `er-evidence:3aebf9384d47efd5daac4e2bc465ca4d8d9550b7d1e463ad7ba06c50b0ba0b04` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:98`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 217 — Researcher

- **pairId:** `resolution-pair:11f74a27697edad42e9ef9cd6651f92efd872c5c12cf62034ec1b848cb50c458`
- **evidenceHash:** `952e69668552e4bd3dc8d67a62326ada056f3ff606d8e22837c752096c094b4f`
- **Question:** do mention A `mention:openalex:W2904324473#1` and B `mention:openalex:W4311994618#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2904324473#1 | mention:openalex:W4311994618#1 |
| Name as written | Michael Benedikt | Michael Benedikt |
| Author position | 1 of 1 | 1 of 5 |
| ORCID on mention | 0000-0003-2964-0880 (OpenAlex-supplied) | 0000-0003-2964-0880 (OpenAlex-supplied) |
| OpenAlex author ID | A5037774973 | A5037774973 |
| Affiliation | ROR 052gg0110 | ROR 052gg0110 |
| Work title | Logic-based Perspectives on Query Reformulationover Restricted Interfaces | Rewriting the infinite chase |
| Year | 2018 | 2022 |
| Venue ID | venue:openalex:S47508943 | venue:openalex:S4210226185 |
| DOI | 10.1145/3299887.3299889 | 10.14778/3551793.3551851 |
| Coauthors | — | Maxime Buron, Stefano Germano, Kevin Kappelmann, Boris Motik |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['052gg0110'] B=['052gg0110'] shared=['052gg0110']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Michael Benedikt" with ROR 052gg0110 on logic-based query reformulation/rewriting work ("Logic-based Perspectives on Query Reformulation over Restricted Interfaces" 2018; "Rewriting the infinite chase" 2022).

**Supporting evidence:**
- Name exact match: author#1 in both
- enrichment ror=052gg0110 on both target mentions
- Topic continuity: logic-based query reformulation/rewriting
- Same OpenAlex-supplied observedOrcid 0000-0003-2964-0880 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors (A is single-authored)

**Limitations / missing information:**
- Relies on name, affiliation and topic; a reviewer may prefer uncertain

<details><summary>Evidence references</summary>

- A `work` `er-evidence:0ef77317d84c100171fe86ce78fa7976f99ec20778a7f3a6a1fcba9f488110ab` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:370`
- A `enrichment` `er-evidence:8b39532294c98ed2f7dc215f83ada1247b78556efd92331c044db0cbed8a1dae` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3845`
- B `enrichment` `er-evidence:680578fdfa824647cb23600d4fbb8e2e26e679e6bc29906a8c018be7305e8fce` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1362`
- B `work` `er-evidence:d5e2eaaadb905d03baa7c676f0ae505d544cb44b645f4f0ba7af46badd1985df` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:126`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 218 — Researcher

- **pairId:** `resolution-pair:3d490a93a2f5484de78261c5fa6ca1cc3d66aabcf83102a3e6e1874e3252e641`
- **evidenceHash:** `373dbb1f2eb9aadfa40f577ab2637dd40c8f75882ebc3a90c3be9435908a8a0d`
- **Question:** do mention A `mention:openalex:W3128793550#4` and B `mention:openalex:W4400909749#6` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3128793550#4 | mention:openalex:W4400909749#6 |
| Name as written | Yuxiang Wang | Yong Wang |
| Author position | 4 of 4 | 6 of 6 |
| ORCID on mention | 0000-0003-3240-2912 (OpenAlex-supplied) | 0009-0005-0906-8778 (OpenAlex-supplied) |
| OpenAlex author ID | A5100394398 | A5101762937 |
| Affiliation | ROR 0576gt767 | — |
| Work title | A comprehensive survey and experimental comparison of graph-based approximate nearest neighbor search | CAGRA: Highly Parallel Graph Construction and Approximate Nearest Neighbor Search for GPUs |
| Year | 2021 | 2024 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210210321 |
| DOI | 10.14778/3476249.3476255 | 10.1109/icde60146.2024.00323 |
| Coauthors | Mengzhao Wang, Xiaoliang Xu, Qiang Yue | Hiroyuki Ootomo, Akira Naruse, Corey Nolet, Ray Wang, Tamas Feher |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['0576gt767'] B=- shared=none_

**AI-proposed label: `different`**

**Note:** A author#4 "Yuxiang Wang" and B author#6 "Yong Wang" have different given names; no coauthor overlap.

**Supporting evidence:**
- nameText given names differ: "Yuxiang" vs "Yong"
- No shared coauthors
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- Both on approximate nearest neighbor search (2021 survey; 2024 GPU method)

**Limitations / missing information:**
- B has no affiliation evidence

<details><summary>Evidence references</summary>

- A `work` `er-evidence:40672fb5014082ff5772844d805e3dc53e79b18a113d69592ac7f27bbae479d4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:222`
- A `enrichment` `er-evidence:7b3d43708479dfb0052b333590592ee09f19f857963d1183ffe7cc1ea6e2525f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2426`
- B `work` `er-evidence:1bf5bf18fdd700f45ad7266e084cc85448ca79dc7a483fdc361cb436d6c35685` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:29`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 219 — Work

- **pairId:** `resolution-pair:85dfbad08bfcf8fd8439cabd90e7de1001688dee83e5e757e2fe32724da9d9c5`
- **evidenceHash:** `749b2ad646ef7c835abf77e4b1b6c3f722ea738de09aa23fd75b80600f3d0c27`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0002-6698-2735/work/60530667 | OPENALEX W2799059383 (conference-paper) |
| Title | Cypher: An Evolving Query Language for Property Graphs | Cypher |
| Year | publicationYear=2018 | 2018 |
| Venue ID | — | venue:openalex:S4393915683 |
| DOI | 10.1145/3183713.3190657 | 10.1145/3183713.3190657 |
| arXiv ID | — | — |
| Pages | — | 1433-1445 |
| Authors | ORCID record owner 0000-0002-6698-2735 (author list not supplied) | (10) Nadime Francis, Alastair Green, Paolo Guagliardo, Leonid Libkin, Tobias Lindaaker, Victor Marsault, Stefan Plantikow, Mats Rydberg, Petra Selmer, Andrés Taylor |
| Observed identifiers | source-work-id=96b066e5-eacd-43b2-9925-1ec2a7e06a8b (self); eid=2-s2.0-85048416577 (self); doi=10.1145/3183713.3190657 (self); isbn=9781450347037 (part-of) | namespace=openalex.doi, value=https://doi.org/10.1145/3183713.3190657, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3183713.3190657, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3183713.3190657'] B=['10.1145/3183713.3190657'] -> equal_

**AI-proposed label: `same`**

**Note:** ORCID activity 0000-0002-6698-2735/work/60530667 ("Cypher: An Evolving Query Language for Property Graphs", 2018) and OpenAlex work "Cypher" (2018) share DOI 10.1145/3183713.3190657; the OpenAlex title is a truncated form.

**Supporting evidence:**
- Normalized DOI equal: 10.1145/3183713.3190657
- Year 2018 on both
- OpenAlex title "Cypher" is the prefix of the ORCID title

**Conflicting evidence:**
- Title strings differ in length (truncation)

**Limitations / missing information:**
- ORCID activity has no author list

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:d779605f8c65a6808a2f61d40fb42f03ec9f534c24b201de401bdd3e500eaa50` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:415`
- B `work` `er-evidence:52f0cea247349bbbd268e1c601286cf07e02ec92fd4e352d3e153e83b06ed927` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:412`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 220 — Work

- **pairId:** `resolution-pair:02f365bd12dc7ac22e66eb3da07807955c52d27a074bfabbbc5885b0cac697d4`
- **evidenceHash:** `0ee23763aeaff59a54f6a8facbac609a8854f95faa5c8ce5e145635adb8ce02f`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-1547-2847/work/113367151 | ORCID activity 0000-0003-1547-2847/work/119514227 |
| Title | Stateful-CCSH: An Efficient Authentication Scheme for High-Resolution Video Surveillance System | Stateful-CCSH: An Efficient Authentication Scheme for High-Resolution Video Surveillance System |
| Year | publicationYear=2022 | publicationYear=2022 |
| Venue ID | — | — |
| DOI | 10.1109/jiot.2022.3165365 | 10.1109/jiot.2022.3165365 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0003-1547-2847 (author list not supplied) | ORCID record owner 0000-0003-1547-2847 (author list not supplied) |
| Observed identifiers | doi=10.1109/jiot.2022.3165365 (self) | doi=10.1109/JIOT.2022.3165365 (self) |

_helper: normalized DOI A=['10.1109/jiot.2022.3165365'] B=['10.1109/jiot.2022.3165365'] -> equal_

**AI-proposed label: `same`**

**Note:** Two activities on ORCID record 0000-0003-1547-2847 carry the same DOI 10.1109/jiot.2022.3165365, the identical title "Stateful-CCSH: An Efficient Authentication Scheme for High-Resolution Video Surveillance System" and publicationYear 2022.

**Supporting evidence:**
- Normalized observedDoi equal
- Identical title
- Same year and ORCID record owner

**Conflicting evidence:**
- Distinct activity ids (duplicate entries)

**Limitations / missing information:**
- No author list, venue or pages

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:8c797489432600914003db60fd6a248de3e108a2d487657f9d55a08ea3cb27a8` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:229`
- B `orcid-activity` `er-evidence:0046b753de8f49f0d5dc78fd5ddc6e7d825f3f959c66ed5327cdafc51033d030` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:237`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

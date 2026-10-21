# ScholarChain AI review drafts — batch 08 (tasks 141–160)

> **Status: AI_SUGGESTIONS_PENDING_HUMAN_REVIEW.** These are AI-generated suggestions from a session-reported `claude-opus-5-5` model (not independently verified). They are not human reviews or gold labels. Record your own decision in each task's decision box; an empty box means not reviewed.

Queue: `review-queue:05c5817f62a70d378829be361b9c9169fc9af18448f7c83c245f1d65bbca6175`  
Work tasks: 10 · Researcher tasks: 10

Rows marked `>> … <<` in the raw data and the 'Name as written' row identify the mention being compared. OpenAlex author IDs and OpenAlex-supplied ORCIDs are provider hypotheses. Lines in _italics_ starting with 'helper:' are exact-string comparisons computed by a script to help reading; they are not judgments.

---
## Task 141 — Researcher

- **pairId:** `resolution-pair:720b7dca0e190296774e2e8cfe2ea03c35af54d108386e9f738d6e29bcaa44bd`
- **evidenceHash:** `3f4e22a669fffbb01c88688cc2018fdafb8bb19eb05c69de496f9fc415ee3caa`
- **Question:** do mention A `mention:openalex:W2889284307#4` and B `mention:openalex:W3145232008#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2889284307#4 | mention:openalex:W3145232008#3 |
| Name as written | Paul Suganthan G. C. | Paul Suganthan G.C. |
| Author position | 4 of 10 | 3 of 15 |
| ORCID on mention | — | — |
| OpenAlex author ID | A5104217740 | A5104217740 |
| Affiliation | ROR 01y2jtd41 | ROR 01y2jtd41 |
| Work title | Cloudmatcher | Technical Perspective: |
| Year | 2018 | 2018 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S47508943 |
| DOI | 10.14778/3229863.3236255 | 10.1145/3277006.3277015 |
| Coauthors | Yash Govind, Erik Paulson, Palaniappan Nagarajan, AnHai Doan, Youngchoon Park, Glenn M. Fung, Devin Conathan, Marshall Carter, Mingju Sun | Pradap Konda, Sanjib Das, Philip Martinkus, Adel Ardalan, Jeffrey R. Ballard, Yash Govind, Han Li, Fatemah Panahi, Haojun Zhang, Jeff Naughton, Shishir Prasad, Ganesh Krishnan, Rohit Deep, Vijay Raghavendra |

_helper: shared coauthor normalizedNames = ['yash govind']_
_helper: target-mention ROR A=['01y2jtd41'] B=['01y2jtd41'] shared=['01y2jtd41']_

**AI-proposed label: `same`**

**Note:** A "Paul Suganthan G. C." and B "Paul Suganthan G.C." differ only in spacing; both 2018 entity-matching-group papers share coauthor Yash Govind and ROR 01y2jtd41.

**Supporting evidence:**
- Name match apart from spacing of the initials
- Shared coauthor in payload: Yash Govind
- enrichment ror=01y2jtd41 on both target mentions
- Same OpenAlex author id A5104217740 (provider hypothesis only)
- Topic: entity matching tooling ("Cloudmatcher"; Magellan-group perspective)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B title is truncated ("Technical Perspective:")
- No ORCID on either mention

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:7099688cbde3f25abe489a4128db27099884ec0f25b81d638a426560fee299bc` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4086`
- A `work` `er-evidence:cafc671d97388165a3db2de939bbeb8cfbc28cc0b65efb05fac5940e97b7d802` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:400`
- B `enrichment` `er-evidence:0079cabfc1ddbffa851edb301f9b0aec470f07521ba7d2e516294dceaae515ce` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2374`
- B `work` `er-evidence:b13c23e42fcaedcadc0070447130bdb28189aac6c7b466d69ea79e91cff520be` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:218`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 142 — Work

- **pairId:** `resolution-pair:382e1d178138b54d285424b8791aea54337a4cdf30955766598f7a952f1ad377`
- **evidenceHash:** `3de40f0788cba9ac96896c31f927356fafd0b8ca26e2e535c5d480671e0851b9`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2963431420 (conference-paper) | OPENALEX W3100857721 (article) |
| Title | Collecting and Analyzing Multidimensional Data with Local Differential Privacy | Achieving 100Gbps Intrusion Prevention on a Single Server |
| Year | 2019 | 2020 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4306420647 |
| DOI | 10.1109/icde.2019.00063 | — |
| arXiv ID | — | — |
| Pages | 638-649 | 1083-1100 |
| Authors | (8) Ning Wang, Xiaokui Xiao, Yin Yang, Jun Zhao, Siu Cheung Hui, Hyejin Shin, Junbum Shin, Ge Yu | (6) Zhipeng Zhao, Hugo Sadok, Nirav Atre, James C. Hoe, Vyas Sekar, Justine Sherry |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde.2019.00063, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde.2019.00063, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1109/icde.2019.00063'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Collecting and Analyzing Multidimensional Data with Local Differential Privacy" (DOI 10.1109/icde.2019.00063, 2019) and B "Achieving 100Gbps Intrusion Prevention on a Single Server" (no DOI, OSDI 2020) have unrelated titles, different years and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2019 vs 2020
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:ec3e4de73bbb8fd85736344e239e8959865b9a4abff9cfd2df326339630b30b0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:329`
- B `work` `er-evidence:557d3c47300f585e43d8245d73b852042641b606dbe4ad1eebea4c79a4fa1e11` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:230`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 143 — Work

- **pairId:** `resolution-pair:f61e2f47ec21d4f7912b7ef841f947263d767d5ceb7650062f345366cd6022db`
- **evidenceHash:** `8af371d1e5226d4637075c2e66de3fa9c0908021cfa1ff2a0068115946e7e2d0`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2795089200 (conference-paper) | OPENALEX W3095227533 (article) |
| Title | Aurum: A Data Discovery System | Twine: A Unified Cluster Management System for Shared Infrastructure |
| Year | 2018 | 2020 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4306420647 |
| DOI | 10.1109/icde.2018.00094 | — |
| arXiv ID | — | — |
| Pages | 1001-1012 | 787-803 |
| Authors | (6) Raul Castro Fernandez, Ziawasch Abedjan, Famien Koko, Gina Yuan, Samuel Madden, Michael Stonebraker | (20) Chunqiang Tang, Kenny Yu, Kaushik Veeraraghavan, Jonathan Kaldor, Scott Michelson, Thawan Kooburat, Aravind Anbudurai, Matthew Clark, Kabir Gogia, Long Cheng, Ben Christensen, Alex Gartrell, Maxim Khutornenko, Sachin Kulkarni, Marcin Pawłowski … (+5 more) |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde.2018.00094, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde.2018.00094, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1109/icde.2018.00094'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Aurum: A Data Discovery System" (DOI 10.1109/icde.2018.00094, 2018) and B "Twine: A Unified Cluster Management System for Shared Infrastructure" (no DOI, OSDI 2020) have different titles, years and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2018 vs 2020
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:bb3939db433f43a6cc3d783e831e2f1442eb02bbda4981b577d54f3a71412bec` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:430`
- B `work` `er-evidence:89c723a4492d89040048728e01108ac1620308c9f1ddb4728304675c3e7d5bb0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:249`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 144 — Work

- **pairId:** `resolution-pair:4559b102d33329f6d95cfc9fab93725ff05ab59ac41a8d3f731aac3dd4ca890a`
- **evidenceHash:** `922e3d53acdb097c611cc51f9b8e82140a6a60c3568aa7134813ec4d0592f0c3`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3176147180 (article) | OPENALEX W4402043038 (article) |
| Title | SONIC: Application-aware Data Passing for Chained Serverless Applications | Combining Small Language Models and Large Language Models for Zero-Shot NL2SQL |
| Year | 2021 | 2024 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210226185 |
| DOI | — | 10.14778/3681954.3681960 |
| arXiv ID | — | — |
| Pages | 973-988 | 2750-2763 |
| Authors | (6) Ashraf Mahgoub, Karthick Shankar, Subrata Mitra, Ana Klimovic, Somali Chaterji, Saurabh Bagchi | (10) Ju Fan, Zihui Gu, Songyue Zhang, Yuxin Zhang, Zui Chen, Lei Cao, Guoliang Li, Samuel Madden, Xiaoyong Du, Nan Tang |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.14778/3681954.3681960, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3681954.3681960, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.14778/3681954.3681960'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "SONIC: Application-aware Data Passing for Chained Serverless Applications" (no DOI, 2021) and B "Combining Small Language Models and Large Language Models for Zero-Shot NL2SQL" (10.14778/3681954.3681960, 2024) have unrelated titles and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2021 vs 2024
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:7d69e1dc64a8cc33f6576fe2fb237114230b3cd706958ff42233dd1c39389cfc` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:194`
- B `work` `er-evidence:eac927034deb68a4c47259836c0c94161022705316b86d5597490a22a4dfa064` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:18`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 145 — Researcher

- **pairId:** `resolution-pair:4aaa1614306b692146b40dca43717e8c70bc76ff708cc144af7c88bdf0bc4f24`
- **evidenceHash:** `043fcaff3d3d70548306bef67b77beb8515194f116741fb9b1c0340c4bde47aa`
- **Question:** do mention A `mention:openalex:W3007813770#3` and B `mention:openalex:W3049595782#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3007813770#3 | mention:openalex:W3049595782#3 |
| Name as written | Xiaokui Xiao | Xiaokui Xiao |
| Author position | 3 of 5 | 3 of 5 |
| ORCID on mention | 0000-0003-0914-4580 (OpenAlex-supplied) | — |
| OpenAlex author ID | A5010903591 | — |
| Affiliation | ROR 01tgyzw49 | ROR 01tgyzw49 |
| Work title | Homogeneous network embedding for massive graphs via reweighted personalized PageRank | Privacy preserving vertical federated learning for tree-based models |
| Year | 2020 | 2020 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210226185 |
| DOI | 10.14778/3377369.3377376 | 10.14778/3407790.3407811 |
| Coauthors | Renchi Yang, Jieming Shi, Yin Yang, Sourav S. Bhowmick | Yuncheng Wu, Shaofeng Cai, Gang Chen, Beng Chin Ooi |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01tgyzw49'] B=['01tgyzw49'] shared=['01tgyzw49']_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Xiaokui Xiao" with ROR 01tgyzw49 in 2020 VLDB papers, but no coauthor is shared and topics differ (network embedding via personalized PageRank; privacy-preserving vertical federated learning).

**Supporting evidence:**
- Name exact match: author#3 in both
- enrichment ror=01tgyzw49 on both target mentions
- Same year 2020 and venueId S4210226185

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- B mention has no ORCID; A observedOrcid is OpenAlex-supplied only
- Name plus affiliation alone stays below the agreed bar

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:16c87eaa7885907e0070060be54e0a2cb6b0dc869f91efb34e6e17dd9c7b6a7d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3176`
- A `work` `er-evidence:1ffc5ba69cec87947308dd8ea11bc0a6ff98694793aa940182145d7b3ceac9a3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:299`
- B `work` `er-evidence:5827c73c0b8de9f6830a983e69817bc6080f425cc20ea20dbc32021a83e863f2` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:262`
- B `enrichment` `er-evidence:6244a9623195e713e58e53eafe6e14e81265ba97c50856409dab0f338dc5da47` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2869`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Both DOIs are listed in ORCID record 0000-0003-0914-4580 (Xiaokui Xiao, pub.orcid.org) and Semantic Scholar assigns the same author ID on both papers (api.semanticscholar.org).

---

## Task 146 — Work

- **pairId:** `resolution-pair:68b59320edff58329237f8eeee46e593136f74374ef7f4357ff5d1802b0796a6`
- **evidenceHash:** `2475a83b9d721d4d4dea384b1e4576c6208db314f0627e7db78cfb9e06378855`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3013555795 (article) | OPENALEX W3095227533 (article) |
| Title | DeepDB | Twine: A Unified Cluster Management System for Shared Infrastructure |
| Year | 2020 | 2020 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4306420647 |
| DOI | 10.14778/3384345.3384349 | — |
| arXiv ID | — | — |
| Pages | 992-1005 | 787-803 |
| Authors | (6) Benjamin Hilprecht, Andreas Schmidt, Moritz Kulessa, Alejandro Molina, Kristian Kersting, Carsten Binnig | (20) Chunqiang Tang, Kenny Yu, Kaushik Veeraraghavan, Jonathan Kaldor, Scott Michelson, Thawan Kooburat, Aravind Anbudurai, Matthew Clark, Kabir Gogia, Long Cheng, Ben Christensen, Alex Gartrell, Maxim Khutornenko, Sachin Kulkarni, Marcin Pawłowski … (+5 more) |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3384345.3384349, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3384345.3384349, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.14778/3384345.3384349'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "DeepDB" (DOI 10.14778/3384345.3384349, VLDB 2020) and B "Twine: A Unified Cluster Management System for Shared Infrastructure" (no DOI, OSDI 2020) have different titles, venues and disjoint authors.

**Supporting evidence:**
- work.title different
- venueId S4210226185 vs S4306420647
- work.authors disjoint

**Conflicting evidence:**
- Same year 2020

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:a750cfe48085a827607af5cab7d7dd9a37b36d996373d133cf988ea2d576a723` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:291`
- B `work` `er-evidence:89c723a4492d89040048728e01108ac1620308c9f1ddb4728304675c3e7d5bb0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:249`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 147 — Work

- **pairId:** `resolution-pair:d9b37dd419080d34027f031836e968d13e8036723e34091274f84f1138b170cc`
- **evidenceHash:** `3c993ff42d2df416a514bda777cf589f989f6f41a47eebe2677d125e985cccd6`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3095227533 (article) | OPENALEX W4400909953 (conference-paper) |
| Title | Twine: A Unified Cluster Management System for Shared Infrastructure | Adapting Large Language Models by Integrating Collaborative Semantics for Recommendation |
| Year | 2020 | 2024 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210210321 |
| DOI | — | 10.1109/icde60146.2024.00118 |
| arXiv ID | — | — |
| Pages | 787-803 | 1435-1448 |
| Authors | (20) Chunqiang Tang, Kenny Yu, Kaushik Veeraraghavan, Jonathan Kaldor, Scott Michelson, Thawan Kooburat, Aravind Anbudurai, Matthew Clark, Kabir Gogia, Long Cheng, Ben Christensen, Alex Gartrell, Maxim Khutornenko, Sachin Kulkarni, Marcin Pawłowski … (+5 more) | (7) Bowen Zheng, Yupeng Hou, Hongyu Lu, Yu Chen, Wayne Xin Zhao, Ming Chen, Ji-Rong Wen |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1109/icde60146.2024.00118, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde60146.2024.00118, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.1109/icde60146.2024.00118'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Twine: A Unified Cluster Management System for Shared Infrastructure" (no DOI, 2020) and B "Adapting Large Language Models by Integrating Collaborative Semantics for Recommendation" (10.1109/icde60146.2024.00118, 2024) have unrelated titles and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2020 vs 2024
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:89c723a4492d89040048728e01108ac1620308c9f1ddb4728304675c3e7d5bb0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:249`
- B `work` `er-evidence:a82d51106e187740ffbf08b5e852ff1d8191d23dd2e5a531341fa734870c6efe` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:26`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 148 — Work

- **pairId:** `resolution-pair:ebf07157a8fba69763a022a71b4d9aa9af61a65c028449d7bbd65febf0916468`
- **evidenceHash:** `ea7ffa745eec332016d5c647ef9082ff189dafb8ef2e18759d09d77551e3eb09`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W4389539730 (article) | OPENALEX W4400909749 (conference-paper) |
| Title | Language Models Enable Simple Systems for Generating Structured Views of Heterogeneous Data Lakes | CAGRA: Highly Parallel Graph Construction and Approximate Nearest Neighbor Search for GPUs |
| Year | 2023 | 2024 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210210321 |
| DOI | 10.14778/3626292.3626294 | 10.1109/icde60146.2024.00323 |
| arXiv ID | — | — |
| Pages | 92-105 | 4236-4247 |
| Authors | (7) Simran Arora, Brandon Yang, Sabri Eyuboglu, Avanika Narayan, Andrew Hojel, Immanuel Trummer, Christopher Ré | (6) Hiroyuki Ootomo, Akira Naruse, Corey Nolet, Ray Wang, Tamas Feher, Yong Wang |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3626292.3626294, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3626292.3626294, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1109/icde60146.2024.00323, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde60146.2024.00323, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.14778/3626292.3626294'] B=['10.1109/icde60146.2024.00323'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Language Models Enable Simple Systems for Generating Structured Views of Heterogeneous Data Lakes" (10.14778/3626292.3626294, 2023) and B "CAGRA: Highly Parallel Graph Construction and Approximate Nearest Neighbor Search for GPUs" (10.1109/icde60146.2024.00323, 2024) have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2023 vs 2024
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:b52af49df5e710c14d8349165a45d91793cb3fceb4b5312cc67eb17813b99805` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:55`
- B `work` `er-evidence:1bf5bf18fdd700f45ad7266e084cc85448ca79dc7a483fdc361cb436d6c35685` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:29`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 149 — Researcher

- **pairId:** `resolution-pair:9a94dc01569914efd17bf03e3f5566e7fd0ec26e6bde399f06c5bfbf5d292e0f`
- **evidenceHash:** `2dc6e5403496442b8764a2b6a855d44de93b047af29280b1afab6f97713ced7b`
- **Question:** do mention A `mention:crossref:10.1145/3277006.3277015#10` and B `mention:openalex:W4385283024#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:crossref:10.1145/3277006.3277015#10 | mention:openalex:W4385283024#2 |
| Name as written | Haojun Zhang | Hanyuan Zhang |
| Author position | 10 of 15 | 2 of 4 |
| ORCID on mention | — | 0000-0002-0862-8316 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5101435256 |
| Affiliation | "University of Wisconsin-Madison" | ROR 013q1eq08 |
| Work title | Technical Perspective: | RNTrajRec: Road Network Enhanced Trajectory Recovery with Spatial-Temporal Transformer |
| Year | 2018 | 2023 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S4210210321 |
| DOI | 10.1145/3277006.3277015 | 10.1109/icde55515.2023.00069 |
| Coauthors | Pradap Konda, Sanjib Das, Paul Suganthan G.C., Philip Martinkus, Adel Ardalan, Jeffrey R. Ballard, Yash Govind, Han Li, Fatemah Panahi, Jeff Naughton, Shishir Prasad, Ganesh Krishnan, Rohit Deep, Vijay Raghavendra | Yuqi Chen, Weiwei Sun, Baihua Zheng |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=- B=['013q1eq08'] shared=none_

**AI-proposed label: `different`**

**Note:** A Crossref author#10 "Haojun Zhang" (organizationName "University of Wisconsin-Madison") and B author#2 "Hanyuan Zhang" have different given names; no coauthor overlap.

**Supporting evidence:**
- nameText given names differ: "Haojun" vs "Hanyuan"
- No shared coauthors
- Topics differ: entity-matching perspective vs road-network trajectory recovery

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- Affiliation forms not comparable (organization name vs ROR 013q1eq08)

<details><summary>Evidence references</summary>

- A `mention-affiliation` `er-evidence:b7d2f150e0b9d7f917ea45708ce146108c4c2589f432d22fc3f7197f1f8004a8` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/mention-affiliation/part-r-00000:27`
- A `work` `er-evidence:d6ba62944b356bd49de3d9d2907bda7733cb2ed1cdc6e17aaac2df0510b6cdc1` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:6`
- B `enrichment` `er-evidence:a94ff21395b513007733461df6ce51220ef6bacc0d1de652819ce39a56de19e6` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:967`
- B `work` `er-evidence:fafd5ddabfd16f3687047ff603ada1b153a3d15a296181b6a98dcafa573f786a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:88`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 150 — Work

- **pairId:** `resolution-pair:f775dd776f61b4a60a16b5473346b72cc660e194ecd879f03600f86a806102e3`
- **evidenceHash:** `2c2f1ddaef6fbb083250e17aa969d12fbddc9ebdaf0bc6ad58e8c888df2c70bf`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-0832-116X/work/151681284 | ORCID activity 0000-0003-0832-116X/work/151681287 |
| Title | Probabilistic Automata of Bounded Ambiguity | Probabilistic automata of bounded ambiguity |
| Year | publicationYear=2022 | publicationYear=2022 |
| Venue ID | — | — |
| DOI | 10.4230/lipics.concur.2017.19 | 10.1016/j.ic.2020.104648 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0003-0832-116X (author list not supplied) | ORCID record owner 0000-0003-0832-116X (author list not supplied) |
| Observed identifiers | doi=10.4230/LIPICS.CONCUR.2017.19 (self); wosuid=WOS:001570554100019 (self) | doi=10.1016/J.IC.2020.104648 (self); wosuid=WOS:000740671600010 (self) |

_helper: normalized DOI A=['10.4230/lipics.concur.2017.19'] B=['10.1016/j.ic.2020.104648'] -> DISTINCT_

**AI-proposed label: `uncertain`** — flags: `IDENTIFIER_CONFLICT`, `VERSION_RELATIONSHIP`

**Note:** Both ORCID activities on record 0000-0003-0832-116X are titled "Probabilistic Automata of Bounded Ambiguity", but they carry distinct DOIs: 10.4230/lipics.concur.2017.19 (a CONCUR 2017 proceedings DOI) and 10.1016/j.ic.2020.104648 (a journal DOI). This looks like a conference paper and its journal version, which the evidence cannot resolve as one publication.

**Supporting evidence:**
- orcid-activity.title identical apart from capitalization
- Same ORCID record owner 0000-0003-0832-116X (ORCID-sourced)
- publicationYear 2022 on both

**Conflicting evidence:**
- Distinct normalized DOIs: 10.4230/lipics.concur.2017.19 vs 10.1016/j.ic.2020.104648
- Distinct wosuid: WOS:001570554100019 vs WOS:000740671600010

**Limitations / missing information:**
- A publicationYear 2022 is inconsistent with the 'concur.2017' DOI string; the ORCID year may be unreliable
- No author lists, venues or pages supplied

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:4d2dfa791f0d382bc59d103a973c5ad779782aa8e3a43fed3e8018cf7c799bd9` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:325`
- B `orcid-activity` `er-evidence:04517688dfc1ca6db68e6167e73a2d78b3b41b8061c1b30e45006ff78b9a14d4` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:322`

</details>

**Danny's decision:** ☐ same ☐ different ☑ uncertain

**Comments:**

> 

---

## Task 151 — Researcher

- **pairId:** `resolution-pair:4ddaa6cee0b9209e0f71504b03ccf695e0efd0e24508d47ac89dae49e32da8b8`
- **evidenceHash:** `378be808a263bf85b025d5648b2bfc11d0c576a3105e239ed4b84d9ed3ec93af`
- **Question:** do mention A `mention:openalex:W2797862701#15` and B `mention:openalex:W3181897344#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2797862701#15 | mention:openalex:W3181897344#2 |
| Name as written | Yuhao Yang | Yuntian Yang |
| Author position | 15 of 20 | 2 of 5 |
| ORCID on mention | 0000-0001-7225-1886 (OpenAlex-supplied) | — |
| OpenAlex author ID | A5050946054 | — |
| Affiliation | ROR 01ek73717 | ROR 02t274463 |
| Work title | BigDL | Addra: Metadata-private voice communication over fully untrusted infrastructure. |
| Year | 2019 | 2021 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4306420647 |
| DOI | 10.1145/3357223.3362707 | — |
| Coauthors | Jason Jinquan Dai, Yiheng Wang, Xin Qiu, Ding Ding, Yao Zhang, Yanzhang Wang, Xianyan Jia, Cherry Li Zhang, Yan Wan, Zhichao Li, Jiao Wang, Shengsheng Huang, Zhongyuan Wu, Yang Wang, Bowen She, Dongjie Shi, Qi Lu, Kai Huang, Guoqiong Song | Ishtiyaque Ahmad, Divyakant Agrawal, Amr El Abbadi, Trinabh Gupta |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01ek73717'] B=['02t274463'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#15 "Yuhao Yang" and B author#2 "Yuntian Yang" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Yuhao" vs "Yuntian"
- No shared coauthors
- enrichment ror differs: 01ek73717 vs 02t274463

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B mention has no ORCID

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:2032826006f61171ed19a14c28483b14264fd797715ab6d5ff9b6eceae76b3c0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4294`
- A `work` `er-evidence:7f23ff95eec85ee7e1670f4b0e01e515a25005e60fdf9568ca996325d47d0dc5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:422`
- B `work` `er-evidence:216c341b63b697c447cd8e4c5051a30dc178ac930724d4504496026fbc771783` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:185`
- B `enrichment` `er-evidence:555eae4644f009dcc0a4e34cb52ffa73e54828a11e11f4c7c0e86829f743b729` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2028`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 152 — Researcher

- **pairId:** `resolution-pair:ef682ab710dc35119b63b5fa5ff4977d3bc3382b1c4b2619d53f17cac1f0bf3e`
- **evidenceHash:** `f765653d044e4ccfbc5a0c59a772cc9472440dab4c75c2b7997e7ffdca739763`
- **Question:** do mention A `mention:openalex:W2948051378#2` and B `mention:openalex:W4312357089#7` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2948051378#2 | mention:openalex:W4312357089#7 |
| Name as written | Xuntao Cheng | Xiaojun Cheng |
| Author position | 2 of 10 | 7 of 16 |
| ORCID on mention | — | 0009-0004-8708-9788 (OpenAlex-supplied) |
| OpenAlex author ID | A5101024540 | A5110709899 |
| Affiliation | ROR 00k642b80 | — |
| Work title | X-Engine | OceanBase |
| Year | 2019 | 2022 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210226185 |
| DOI | 10.1145/3299869.3314041 | 10.14778/3554821.3554830 |
| Coauthors | Gui Huang, Jianying Wang, Yujie Wang, Dengcheng He, Tieying Zhang, Feifei Li, Sheng Wang, Wei Cao, Qiang Li | Zhenkun Yang, Chuanhui Yang, Fusheng Han, Mingqiang Zhuang, Bing Yang, Zhifeng Yang, Yuzhong Zhao, Wenhui Shi, Huafeng Xi, Huang Yu, Bin Liu, Yi Pan, Boxue Yin, Junquan Chen, Quanqing Xu |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00k642b80'] B=- shared=none_

**AI-proposed label: `different`**

**Note:** A author#2 "Xuntao Cheng" and B author#7 "Xiaojun Cheng" have different given names; no coauthor overlap.

**Supporting evidence:**
- nameText given names differ: "Xuntao" vs "Xiaojun"
- No shared coauthors

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no affiliation evidence; A has no ORCID

<details><summary>Evidence references</summary>

- A `work` `er-evidence:19d0e96eec0f2d8187bc0380a8ee39af1c0570bb3860affa17beff70425a6bba` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:355`
- A `enrichment` `er-evidence:8727db5cfc1d91c0c6f2d0b267fd4b6c45b53f0beb1b1b195cf126a5538f6bed` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3707`
- B `work` `er-evidence:5fd523c89fec071c27aa59adf754e97b144a5f43ab00bbcb08a85578f0f84a23` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:123`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 153 — Researcher

- **pairId:** `resolution-pair:a2b4d0559ad8ab83ffec732e7bcb44c37bfcc98699405e2dacd2179740172208`
- **evidenceHash:** `9cfc92e215a3a8dea67a3b07091314025282c6a8ad284fd9295ba941a0bc9bdd`
- **Question:** do mention A `mention:openalex:W3109841242#1` and B `mention:openalex:W3174809957#7` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3109841242#1 | mention:openalex:W3174809957#7 |
| Name as written | Xuhong Wang | Xiangyu Wang |
| Author position | 1 of 11 | 7 of 22 |
| ORCID on mention | — | — |
| OpenAlex author ID | — | — |
| Affiliation | ROR 0220qvk04; ROR 00g5w7n47 | — |
| Work title | APAN: Asynchronous Propagation Attention Network for Real-time Temporal Graph Embedding | Milvus |
| Year | 2021 | 2021 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4393915683 |
| DOI | 10.1145/3448016.3457564 | 10.1145/3448016.3457550 |
| Coauthors | Ding Lyu, Mengjian Li, Yang Xia, Qi Yang, Xinwen Wang, Xinguang Wang, Ping Cui, Yupu Yang, Bowen Sun, Zhenyu Guo | Jianguo Wang, Xiaomeng Yi, Rentong Guo, Hai Jin, Peng Xu, Shengjun Li, Xiangzhou Guo, Chengming Li, Xiaohai Xu, Kun Yu, Yuxing Yuan, Yinghao Zou, Jiquan Long, Yudong Cai, Zhenxiang Li, Zhifeng Zhang, Yihua Mo, Jun Gu, Ruiyi Jiang, Yi Wei, Charles Xie |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00g5w7n47', '0220qvk04'] B=- shared=none_

**AI-proposed label: `different`**

**Note:** A author#1 "Xuhong Wang" and B author#7 "Xiangyu Wang" have different given names; no coauthor overlap.

**Supporting evidence:**
- nameText given names differ: "Xuhong" vs "Xiangyu"
- No shared coauthors

**Conflicting evidence:**
- Same year 2021 and venueId S4393915683

**Limitations / missing information:**
- Neither mention has an ORCID; B has no affiliation evidence

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:02e3cb683f938f7aa5506814e0de69a741fc030647ad612dd7e1e94d75de3d4a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2482`
- A `enrichment` `er-evidence:28fb57e0665927a7fc5c28a01528f94d8524cdb3dcacc64d5c0d4dfdc8b996f5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2476`
- A `work` `er-evidence:315df73c446e94772b2a939cfcb468a83c73a87d68920076a45ce79129dce0f3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:227`
- B `work` `er-evidence:059c5b77f57296f9c3cfe445c3f1e6590acc71be1c86aeaadbbe71bbcdfcabc4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:202`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 154 — Work

- **pairId:** `resolution-pair:3067cb18189f98d2e132882d6ec666aedad60d25c409f825aa22004e29facd10`
- **evidenceHash:** `c4d394408066239c7f1c5c413e5cb8bf42dc845507d88d2b67e717fa877809db`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3173563914 (article) | OPENALEX W4312285477 (article) |
| Title | DistAI: Data-Driven Automated Invariant Learning for Distributed Protocols. | Manu |
| Year | 2021 | 2022 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210226185 |
| DOI | — | 10.14778/3554821.3554843 |
| arXiv ID | — | — |
| Pages | 405-421 | 3548-3561 |
| Authors | (6) Jianan Yao, Runzhou Tao, Ronghui Gu, Jason Nieh, Suman Jana, Gabriel Ryan | (15) Rentong Guo, Xiaofan Luan, Long Xiang, Xiao Yan, Xiaomeng Yi, Jigao Luo, Qianya Cheng, Weizhi Xu, Jiarui Luo, Frank Liu, Zhenshan Cao, Yanliang Qiao, Ting Wang, Bo Tang, Charles Xie |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.14778/3554821.3554843, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3554821.3554843, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.14778/3554821.3554843'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "DistAI: Data-Driven Automated Invariant Learning for Distributed Protocols." (no DOI, OSDI 2021) and B "Manu" (10.14778/3554821.3554843, 2022) have different titles, years, venues and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2021 vs 2022
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:3db98d591ee891a15936357cc48a569a7bce863c89118ccf3c1819c60e2436d7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:212`
- B `work` `er-evidence:38458648f49124fffd7baa9562597bd5513a7659309225b6bdbf23de3d27122e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:124`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 155 — Researcher

- **pairId:** `resolution-pair:bfc55237ef6296ae115746ead97e1569f76d00e26ed611bcb75786e14e79d4a7`
- **evidenceHash:** `04662f647d5b4f3d000884df386396e6262f3051b31b99662b11415b5fa72899`
- **Question:** do mention A `mention:openalex:W3028864969#3` and B `mention:openalex:W3029532343#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3028864969#3 | mention:openalex:W3029532343#1 |
| Name as written | Ping Li | Pengfei Li |
| Author position | 3 of 3 | 1 of 5 |
| ORCID on mention | 0000-0002-5979-8868 (OpenAlex-supplied) | 0000-0002-1484-0698 (OpenAlex-supplied) |
| OpenAlex author ID | A5100435527 | A5100339743 |
| Affiliation | — | ROR 00a2xv884 |
| Work title | SONG: Approximate Nearest Neighbor Search on GPU | LISA: A Learned Index Structure for Spatial Data |
| Year | 2020 | 2020 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4393915683 |
| DOI | 10.1109/icde48307.2020.00094 | 10.1145/3318464.3389703 |
| Coauthors | Weijie Zhao, Shulong Tan | Hua Lu, Qian Zheng, Long Yang, Gang Pan |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=- B=['00a2xv884'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#3 "Ping Li" and B author#1 "Pengfei Li" have different given names; no coauthor overlap.

**Supporting evidence:**
- nameText given names differ: "Ping" vs "Pengfei"
- No shared coauthors
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- Same year 2020

**Limitations / missing information:**
- A has no affiliation evidence

<details><summary>Evidence references</summary>

- A `work` `er-evidence:1466a1d1d5a108ca8de5ef161f0c92fe4e99b13ee8c9d611b4737b1f7670793f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:286`
- B `work` `er-evidence:5845ecf81e1aea8cd6569dc65a437eb74a641a8427cf37d2eaefc0b5d147b6a1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:282`
- B `enrichment` `er-evidence:90250c6d980762dd24b372df06f997bbc50e75eecf20b62df1fe8b3f3ec3e887` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3044`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 156 — Researcher

- **pairId:** `resolution-pair:755dd479bf73a6eaa2375d1c812484dc375c9e6a0923ea4669e655ed39010393`
- **evidenceHash:** `5608b04dd15b08abacddbbd6ebc55aa28103e7176bac1c478519d31a84ab9fc2`
- **Question:** do mention A `mention:crossref:10.1145/3299887.3299894#1` and B `mention:crossref:10.1145/3299887.3299895#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:crossref:10.1145/3299887.3299894#1 | mention:crossref:10.1145/3299887.3299895#1 |
| Name as written | Marianne Winslett | Marianne Winslett |
| Author position | 1 of 2 | 1 of 2 |
| ORCID on mention | — | — |
| OpenAlex author ID | — | — |
| Affiliation | "University of Illinois Urbana-Champaign, Champaign, IL, USA" | "University of Illinois Urbana-Champaign, Champaign, IL, USA" |
| Work title | Kenneth Ross Speaks Out on Making Contributions that Span Technology and Science | Paris Koutris Speaks Out on a Theoretical Model for Query Processing |
| Year | 2018 | 2018 |
| Venue ID | venue:issn:0163-5808 | venue:issn:0163-5808 |
| DOI | 10.1145/3299887.3299894 | 10.1145/3299887.3299895 |
| Coauthors | Vanessa Braganholo | Vanessa Braganholo |

_helper: shared coauthor normalizedNames = ['vanessa braganholo']_
_helper: target-mention ROR A=- B=- shared=none_

**AI-proposed label: `same`**

**Note:** Both Crossref mentions are author#1 "Marianne Winslett" on 2018 SIGMOD Record (issn 0163-5808) "…Speaks Out…" interviews with the same coauthor Vanessa Braganholo and the identical organizationName "University of Illinois Urbana-Champaign, Champaign, IL, USA".

**Supporting evidence:**
- Name exact match at author#1
- Shared coauthor in payload: Vanessa Braganholo
- Identical Crossref mention-affiliation organizationName
- Same venue issn:0163-5808, same year, adjacent DOIs (…3299894 / …3299895) and pages (41-47 / 48-50)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- No ORCID or other identifier on either mention

<details><summary>Evidence references</summary>

- A `work` `er-evidence:435803cb72545c2b6fe5eeea2c3603e41607ed58676a0bd76902b2743ebae8f3` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:8`
- A `mention-affiliation` `er-evidence:e119d2eca505937f85c249458d2ab0912f28b646ef1a773825b46f95a5539589` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/mention-affiliation/part-r-00000:37`
- B `mention-affiliation` `er-evidence:14997dc29e888f6b38639620c753bcbf1afbc3b462bedc8b2b46b44736c71c52` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/mention-affiliation/part-r-00000:39`
- B `work` `er-evidence:c28efcdad4b3172e70b3cb562d8cfa56e1cf73065a400fdc86d5feacb85659ed` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:9`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 157 — Work

- **pairId:** `resolution-pair:dc6acda50bb82f140fc100ea5bb4fbcb222d6586d553d04536cf226cf905f1c4`
- **evidenceHash:** `c97e41e3f5410bd99392e9d68573515ab4a7c551a12d0d696d7998254b3fc6df`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3174566165 (article) | OPENALEX W4226379841 (conference-paper) |
| Title | Nap: A Black-Box Approach to NUMA-Aware Persistent Memory Indexes | Sherman: A Write-Optimized Distributed B+Tree Index on Disaggregated Memory |
| Year | 2021 | 2022 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4393915683 |
| DOI | — | 10.1145/3514221.3517824 |
| arXiv ID | — | — |
| Pages | 93-111 | 1033-1048 |
| Authors | (4) Qing Wang, Youyou Lu, Junru Li, Jiwu Shu | (3) Qing Wang, Youyou Lu, Jiwu Shu |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3514221.3517824, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3514221.3517824, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.1145/3514221.3517824'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Nap: A Black-Box Approach to NUMA-Aware Persistent Memory Indexes" (no DOI, OSDI 2021) and B "Sherman: A Write-Optimized Distributed B+Tree Index on Disaggregated Memory" (10.1145/3514221.3517824, SIGMOD 2022) have different titles describing different systems, despite three shared authors.

**Supporting evidence:**
- work.title different (Nap vs Sherman)
- work.year 2021 vs 2022; venueId S4306420647 vs S4393915683; pages 93-111 vs 1033-1048

**Conflicting evidence:**
- Three shared authors in the same order: Qing Wang, Youyou Lu, Jiwu Shu (A also has Junru Li)
- Both are index structures for new memory hardware

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:2873ea80b995b181f3d7d3bff511f82977a32037ec5af6e2ffa09aceaba2489e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:206`
- B `work` `er-evidence:a40e0d523db76db5ee9d5e159138b37dde2b0b8d9c5e4d76181077c241526c45` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:158`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 158 — Researcher

- **pairId:** `resolution-pair:1f26ce2332bcad7f29ac808b12fa890f4a8969105bf0aa86a99de7547b9b2191`
- **evidenceHash:** `89608f3102d62b2abb44cab5eaeacbc2825c3e53a01bb2bd35bbbaca52dda8b2`
- **Question:** do mention A `mention:openalex:W2798649495#7` and B `mention:openalex:W3145232008#14` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2798649495#7 | mention:openalex:W3145232008#14 |
| Name as written | Rohit Deep | Rohit Deep |
| Author position | 7 of 9 | 14 of 15 |
| ORCID on mention | — | — |
| OpenAlex author ID | A5084111141 | A5084111141 |
| Affiliation | ROR 04j0gge90 | ROR 04j0gge90 |
| Work title | Deep Learning for Entity Matching | Technical Perspective: |
| Year | 2018 | 2018 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S47508943 |
| DOI | 10.1145/3183713.3196926 | 10.1145/3277006.3277015 |
| Coauthors | Sidharth Mudgal, Han Li, Theodoros Rekatsinas, AnHai Doan, Youngchoon Park, Ganesh Krishnan, Esteban Arcaute, Vijay Raghavendra | Pradap Konda, Sanjib Das, Paul Suganthan G.C., Philip Martinkus, Adel Ardalan, Jeffrey R. Ballard, Yash Govind, Han Li, Fatemah Panahi, Haojun Zhang, Jeff Naughton, Shishir Prasad, Ganesh Krishnan, Vijay Raghavendra |

_helper: shared coauthor normalizedNames = ['ganesh krishnan', 'han li', 'vijay raghavendra']_
_helper: target-mention ROR A=['04j0gge90'] B=['04j0gge90'] shared=['04j0gge90']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Rohit Deep" on 2018 entity-matching papers sharing three coauthors (Han Li, Ganesh Krishnan, Vijay Raghavendra) and the same ROR 04j0gge90.

**Supporting evidence:**
- Name exact match: A author#7, B author#14
- Three shared coauthors
- enrichment ror=04j0gge90 on both target mentions
- Same OpenAlex author id A5084111141 (provider hypothesis only)
- Topic: entity matching ("Deep Learning for Entity Matching")

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B title truncated
- No ORCID on either mention

<details><summary>Evidence references</summary>

- A `work` `er-evidence:06d27db8fd093fcb89e48c5dd0e422fdfbc511fca4f96c5ee3be97d543c2b05b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:419`
- A `enrichment` `er-evidence:ee9b6a4f1420f56c4281b14751eb91a5ea978553254de8974c429a565ad95df5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4254`
- B `work` `er-evidence:b13c23e42fcaedcadc0070447130bdb28189aac6c7b466d69ea79e91cff520be` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:218`
- B `enrichment` `er-evidence:eca98495ece8091f18893912950209eec782ae937b5bcad9bb1315f419500b5e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2382`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 159 — Work

- **pairId:** `resolution-pair:0ed5062c6524c3c8046bcf0cfcd92b16ec438747d505f6824a5522f86b9e4b5c`
- **evidenceHash:** `12026077fc39bfb5d9a0f9c81f190c9d9a2e8f93f6e01a4cbd33f071d3bde99e`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3032789239 (conference-paper) | OPENALEX W3097770476 (article) |
| Title | A Study of the Fundamental Performance Characteristics of GPUs and CPUs for Database Analytics | The CacheLib Caching Engine: Design and Experiences at Scale |
| Year | 2020 | 2020 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4306420647 |
| DOI | 10.1145/3318464.3380595 | — |
| arXiv ID | — | — |
| Pages | 1617-1632 | 753-768 |
| Authors | (3) Anil Shanbhag, Samuel Madden, Xiangyao Yu | (11) Benjamin Wagner vom Berg, Daniel S. Berger, Sara McAllister, Isaac Grosof, Sathya Gunasekar, Jimmy Lu, Michael Uhlar, Jim Carrig, Nathan Beckmann, Mor Harchol‐Balter, Gregory R. Ganger |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3318464.3380595, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3318464.3380595, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1145/3318464.3380595'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "A Study of the Fundamental Performance Characteristics of GPUs and CPUs for Database Analytics" (DOI 10.1145/3318464.3380595, SIGMOD 2020) and B "The CacheLib Caching Engine…" (no DOI, OSDI 2020) have different titles, venues and disjoint authors.

**Supporting evidence:**
- work.title different
- venueId S4393915683 vs S4306420647
- work.authors disjoint

**Conflicting evidence:**
- Same year 2020

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:41bf036644f598fa8f4e9e1193e8a85632ff053530bc6c15df04e477ed0e01a6` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:265`
- B `work` `er-evidence:9077058943211a3d57147957a5b6b8f33c3099382a96b1b8235ebf3c9e6f8024` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:234`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 160 — Researcher

- **pairId:** `resolution-pair:da3251503f61abbeb0d1857d4a10f86479d6e6f695e8def1ffbd5f65c67823c0`
- **evidenceHash:** `b365d392370d5dc60f326452c9029b87e139e1669222cc3e218134b4a0120086`
- **Question:** do mention A `mention:crossref:10.1145/3299887.3299900#2` and B `mention:openalex:W2939050176#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:crossref:10.1145/3299887.3299900#2 | mention:openalex:W2939050176#2 |
| Name as written | Xiaokui Xiaokui Xiao | Xiaokui Xiao |
| Author position | 2 of 2 | 2 of 6 |
| ORCID on mention | — | 0000-0003-0914-4580 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5010903591 |
| Affiliation | "Nanyang Technological University, Nanyang, Singapore" | ROR 01tgyzw49 |
| Work title | DANTE | Efficient Estimation of Heat Kernel PageRank for Local Clustering |
| Year | 2018 | 2019 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S4393915683 |
| DOI | 10.1145/3299887.3299900 | 10.1145/3299869.3319886 |
| Coauthors | Sourav S. Bhowmick | Renchi Yang, Zhewei Wei, Sourav S. Bhowmick, Jun Zhao, Rong-Hua Li |

_helper: shared coauthor normalizedNames = ['sourav s. bhowmick']_
_helper: target-mention ROR A=- B=['01tgyzw49'] shared=none_

**AI-proposed label: `uncertain`**

**Note:** Both mentions share coauthor Sourav S. Bhowmick, but A's Crossref nameText is the irregular "Xiaokui Xiaokui Xiao" and affiliations are not comparable (A organizationName "Nanyang Technological University…" vs B ROR 01tgyzw49).

**Supporting evidence:**
- Shared coauthor in payload: Sourav S. Bhowmick
- Name compatible apart from the duplicated given name in A

**Conflicting evidence:**
- A nameText is irregular

**Limitations / missing information:**
- Affiliation forms not comparable
- Topics not clearly linked ("DANTE" 2018 vs heat-kernel PageRank 2019)
- B observedOrcid is OpenAlex-supplied only

<details><summary>Evidence references</summary>

- A `mention-affiliation` `er-evidence:337e5265b9f5b64f4da5d0db0cd35159c5d69c544cd31150833d01bd2a09d178` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/mention-affiliation/part-r-00000:40`
- A `work` `er-evidence:690d131b6af699b1f16bff88ab11c81b14fbd5b45d538e17840e146128ff4308` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:10`
- B `enrichment` `er-evidence:7263a6e960ca7f975f839d991fca07e02515ba99b261b0a20f9c2828fc594426` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3750`
- B `work` `er-evidence:e0918f64c8eeaf5c71ce8f3e79aac8b3861a06efbe4aa63d02e5c466ae492fa9` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:358`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Both DOIs are listed in ORCID record 0000-0003-0914-4580 (Xiaokui Xiao, pub.orcid.org) and Semantic Scholar assigns the same author ID on both papers (api.semanticscholar.org).

---
